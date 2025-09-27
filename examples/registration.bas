REM =============================================
REM  Advanced User Registration Form
REM =============================================
TRON
FORM NewUserRegistration
  REM Add a main heading and some instructions at the top
  HEADING "Create Your Account"
  TEXTBLOCK "Please fill out the fields below. Fields marked with an asterisk (*) are required."
  SEPARATOR

  REM Use a sub-heading to group related fields
  HEADING "Account Information"
  FIELD login TYPE TEXT LABEL "Login ID*:"       _
    REQUIRED MESSAGE "Login ID is required."     _
    MINLENGTH 6 MESSAGE "Login ID must be at least 6 characters."

  FIELD email TYPE EMAIL LABEL "Email Address*:" _
    REQUIRED MESSAGE "Email is required."        _
    PATTERN "^\S+@\S+\.\S+$" MESSAGE "Please enter a valid email address."

  FIELD pwd TYPE PASSWORD LABEL "Password*:"   _
    REQUIRED MESSAGE "Password is required."

  REM Add another separator and heading for the next section
  SEPARATOR
  HEADING "Personal Details"
  TEXTBLOCK "This information will be displayed on your public profile."
  FIELD fullName TYPE TEXT LABEL "Full Name:"

  FIELD bio TYPE MEMO LABEL "Biography:"                      _
    PLACEHOLDER "Tell us a little about yourself..."          _
    MAXLENGTH 200 MESSAGE "Biography cannot exceed 200 characters."

  BUTTON "Register" ACTION SUBMIT
  BUTTON "Back" ACTION CANCEL
END FORM

REM --- Run the form ---
OPEN FORM NewUserRegistration

IF FORM_RESULT$ = "SUBMIT" THEN
    PRINT "Form submitted successfully!"
    PRINT "Login:"; login$
    PRINT "Email:"; email$
ELSE
    PRINT "Registration cancelled."
END IF