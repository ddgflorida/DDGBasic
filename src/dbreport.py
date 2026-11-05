"""
Report layout for DbBasic's REPORT statement: a title line with date and page
number, column headings, group headers and subtotal footers (nested for
several GROUP BY columns), grand totals, and optional pagination.

build_report() is pure: it takes the query's columns and rows and returns the
report as a list of text lines (a form feed, '\f', starts each new page).
"""

def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _plain(value):
    """A value as PRINT shows it, without the leading space."""
    if value is None:
        return ''
    if _is_number(value):
        f = float(value)
        return str(int(f)) if f == int(f) and abs(f) < 1e15 else repr(f)
    return str(value)


def build_report(columns, rows, title='', groups=(), totals=(), formats=None,
                 page_length=0, date='', format_value=None, max_width=40):
    """Returns the report as a list of lines.

    columns      the query's column names
    rows         the query's rows (sequences, in column order)
    groups       column names to group by, outermost first (the rows must be sorted by them)
    totals       column names to sum in group footers and the grand total
    formats      {column name: FORMAT$ mask}
    page_length  lines per page, or 0 for one long page
    format_value format_value(mask, value) -> text, used for FORMAT masks
    """
    formats = {k.lower(): v for k, v in (formats or {}).items()}
    lower = [c.lower() for c in columns]

    def index_of(name):
        try:
            return lower.index(name.lower())
        except ValueError:
            raise ValueError(f"REPORT: there is no column '{name}' in the query.")

    group_idx = [index_of(g) for g in groups]
    total_idx = [index_of(t) for t in totals]
    shown = [i for i in range(len(columns)) if i not in group_idx]
    if not shown:
        raise ValueError("REPORT: every column is a GROUP BY column; nothing is left to show.")

    def text(i, value):
        mask = formats.get(lower[i])
        if mask and value not in (None, '') and format_value:
            return format_value(mask, value).strip()
        return _plain(value)

    numeric = {i: any(_is_number(r[i]) for r in rows) for i in shown}
    cells = [[text(i, r[i]) for i in shown] for r in rows]

    # Grand and group totals, worked out first so the column widths can fit them
    def total_of(subset, i):
        values = [r[i] for r in subset if _is_number(r[i])]
        return sum(values) if values else 0

    def make_breaks():
        """Group boundaries: a list of (level, start, end) for every group at every level."""
        spans = []
        for level in range(len(group_idx)):
            keys = [tuple(r[g] for g in group_idx[:level + 1]) for r in rows]
            start = 0
            for k in range(1, len(rows) + 1):
                if k == len(rows) or keys[k] != keys[start]:
                    spans.append((level, start, k))
                    start = k
        return spans

    spans = make_breaks()
    total_texts = {i: [text(i, total_of(rows[s:e], i)) for _, s, e in spans] + [text(i, total_of(rows, i))]
                   for i in total_idx}

    widths = []
    for n, i in enumerate(shown):
        w = max([len(str(columns[i]))] + [len(c[n]) for c in cells])
        if i in total_idx:
            w = max([w] + [len(t) for t in total_texts[i]])
        widths.append(min(max_width, w))

    # Footer labels ("East (2)", "Total (4)") go in the columns before the first total;
    # widen the last of those columns so the longest label fits
    first_total = min((shown.index(i) for i in total_idx), default=0)
    if first_total > 0:
        labels = [len('  ' * level + f"{text(group_idx[level], rows[s][group_idx[level]])} ({e - s})")
                  for level, s, e in spans] + [len(f"Total ({len(rows)})")]
        room = sum(widths[:first_total]) + first_total - 1
        if max(labels) > room:
            widths[first_total - 1] += max(labels) - room

    def fit(n, value):
        i = shown[n]
        value = value[:widths[n]]
        return value.rjust(widths[n]) if numeric[i] or i in total_idx else value.ljust(widths[n])

    def line_of(values):
        return ' '.join(fit(n, v) for n, v in enumerate(values)).rstrip()

    heading = ' '.join(str(columns[i])[:widths[n]].rjust(widths[n]) if (numeric[i] or i in total_idx)
                       else str(columns[i])[:widths[n]].ljust(widths[n])
                       for n, i in enumerate(shown)).rstrip()
    rule = ' '.join('-' * w for w in widths)
    report_width = max(len(rule), 40)

    def totals_line(label, subset, mark):
        """A footer: the label in the columns before the first total, then the totals."""
        values = [''] * len(shown)
        for i in total_idx:
            values[shown.index(i)] = text(i, total_of(subset, i))
        first = min((shown.index(i) for i in total_idx), default=len(shown))
        room = sum(widths[:first]) + max(0, first - 1)
        under = ' '.join((mark * widths[n]) if shown[n] in total_idx else ' ' * widths[n]
                         for n in range(len(shown))).rstrip()
        out = [under] if total_idx else []
        body = line_of(values)
        if room >= len(label):
            out.append((label.ljust(room) + body[room:]).rstrip())
        else:
            out.append(label)
            if total_idx:
                out.append(body)
        return out

    # Lay out the body: rows, with group headers before and footers after each group
    body = []
    starts = {}
    ends = {}
    for level, s, e in spans:
        starts.setdefault(s, []).append((level, s, e))
        ends.setdefault(e, []).append((level, s, e))
    for k, cell_row in enumerate(cells):
        for level, s, e in sorted(starts.get(k, []), key=lambda x: x[0]):
            g = group_idx[level]
            body.append('  ' * level + f"{columns[g]}: {text(g, rows[s][g])}")
        body.append(line_of(cell_row))
        for level, s, e in sorted(ends.get(k + 1, []), key=lambda x: -x[0]):
            g = group_idx[level]
            label = '  ' * level + f"{text(g, rows[s][g])} ({e - s})"
            body += totals_line(label, rows[s:e], '-')
            body.append('')
    if total_idx or group_idx:
        body += totals_line(f"Total ({len(rows)})", rows, '=')
    else:
        body.append('')
        body.append(f"({len(rows)} rows)")
    if not rows:
        body = ['(no rows)']

    # Pages: a title line (with date and page number) and the headings at the top of each
    def page_top(number):
        right = f"{date}  Page {number}".strip() if page_length else date
        top = (title + ' ' * max(1, report_width - len(title) - len(right)) + right).rstrip() \
            if (title or right) else ''
        lines = [top, ''] if top else []
        return lines + [heading, rule]

    if not page_length:
        return page_top(1) + body
    lines, page = [], 1
    space = max(1, page_length - len(page_top(1)))
    for n in range(0, max(1, len(body)), space):
        chunk = body[n:n + space]
        top = page_top(page)
        if page > 1:
            top[0] = '\f' + top[0]
        lines += top + chunk
        page += 1
    return lines
