REM =============================================
REM  User Signup Form with Validation
REM =============================================

REM --- 1. DEFINE THE FORM ---
FORM SignupForm
  HEADING "Create Your Account"
  TEXTBLOCK "Please choose a secure username and password."

  FIELD username TYPE TEXT LABEL "Username"        _
    REQUIRED MESSAGE "You must enter a username."   _
    MINLENGTH 5 MESSAGE "Username must be at least 5 characters." _
    MAXLENGTH 20 MESSAGE "Username is too long (max 20 characters)."

  FIELD age TYPE NUMBER LABEL "Age"                _
    REQUIRED MESSAGE "Please enter your age."       _
    MINVALUE 18 MESSAGE "You must be at least 18 years old to sign up."

  FIELD zipCode TYPE TEXT LABEL "ZIP Code (US)"    _
    PATTERN "^\d{5}(-\d{4})?$" MESSAGE "Please enter a valid US ZIP code."

  FIELD pwd TYPE PASSWORD LABEL "Password"         _
    REQUIRED MESSAGE "Password cannot be empty."    _
    MINLENGTH 8 MESSAGE "Password must be at least 8 characters."

  FIELD pwdConfirm TYPE PASSWORD LABEL "Confirm Password"   _
    REQUIRED MESSAGE "Please confirm your password."         _
    MATCHES "pwd" MESSAGE "The passwords do not match."

  BUTTON "Create Account" ACTION SUBMIT
  BUTTON Cancel ACTION CANCEL
END FORM

REM --- 2. RUN THE APPLICATION ---
OPEN FORM SignupForm

IF FORM_RESULT$ = "SUBMIT" THEN
    PRINT "Validation successful! Account would be created for user:"; username$
ELSE
    PRINT "User cancelled the signup form."
END IF