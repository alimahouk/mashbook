let isLoggedIn;
let loginForm;
let loginEmailTextField;
let loginPasswordTextField;
let loginSubmitButton;
let loginWindow;
let navLoginButton;
let navUserRegistrationButton;
let userRegistrationEmailTextField;
let userRegistrationForm;
let userRegistrationPasswordTextField;
let userRegistrationSubmitButton;
let userRegistrationWindow;
let showLoginButton;
let showUserRegisterButton;
let windowActionCloseButtons;
let windowLayer;


const LoginStatus = {
    OK: 0,
    CREDENTIALS_INVALID: 11,
};

const UserRegistrationStatus = {
    OK: 0,
    EMAIL_FORMAT_INVALID: 10,
    PASSWORD_FORMAT_INVALID: 12,
};


document.addEventListener("DOMContentLoaded", function () {
    setUpPage();
});

function dismissAllWindows() {
    var visibleWindows = document.querySelectorAll("#windowLayer .window:not(.hidden)");

    for (const window of visibleWindows) {
        dismissWindow(window);
    }
}

function dismissWindow(window) {
    if (window) {
        window.classList.add("hidden");
        window.classList.remove("inactive");

        const clearableFields = window.querySelectorAll("input.clearable");

        for (const field of clearableFields) {
            field.value = "";
        }

        var visibleWindows = document.querySelectorAll("#windowLayer .window:not(.hidden)");

        if (visibleWindows.length == 0) {
            windowLayer.classList.add("hidden");
        }
    }
}

function getWindowForActionButton(button) {
    var window = null;

    if (button) {
        var element = button;
        var window = null;
        const windowClassName = "window";

        while (element.parentNode) {
            if (element.classList.contains(windowClassName)) {
                window = element;
                break;
            }

            element = element.parentNode;
        }
    }

    return window;
}

function presentWindow(window, dismissAllFirst = true) {
    if (dismissAllFirst) {
        dismissAllWindows();
    }

    if (window) {
        window.classList.remove("hidden");
        window.classList.remove("inactive");
        windowLayer.classList.remove("hidden");

        const focusedFields = window.querySelectorAll("input.autofocus");

        if (focusedFields) {
            focusedFields[0].focus();
        }
    }
}

function setUpPage() {
    if (document.getElementById("mashbook").classList.contains("public")) {
        isLoggedIn = false;
    } else {
        isLoggedIn = true;
    }

    setUpPageBindings();
    setUpPageEventListeners();
}

function setUpPageBindings() {
    if (!isLoggedIn) {
        loginForm = document.loginForm;
        loginEmailTextField = document.loginForm.email_address;
        loginPasswordTextField = document.loginForm.password;
        loginSubmitButton = document.querySelector("#loginSubmitButton");
        loginWindow = document.querySelector("#loginWindow");
        navLoginButton = document.querySelector("#navLoginButton");
        navUserRegistrationButton = document.querySelector("#navUserRegistrationButton");
        showLoginButton = document.querySelector("#showLoginButton");
        showUserRegisterButton = document.querySelector("#showUserRegisterButton");
        userRegistrationEmailTextField = document.userRegistrationForm.email_address;
        userRegistrationForm = document.userRegistrationForm;
        userRegistrationPasswordTextField = document.userRegistrationForm.password;
        userRegistrationSubmitButton = document.querySelector("#userRegistrationSubmitButton");
        userRegistrationWindow = document.querySelector("#userRegistrationWindow");
        windowLayer = document.querySelector("#windowLayer");
    }

    windowActionCloseButtons = [];

    const windowActionButtons = document.querySelectorAll("#windowLayer .window .windowActionButtons");

    for (const buttons of windowActionButtons) {
        const closeActionButton = buttons.getElementsByClassName("close")[0];
        windowActionCloseButtons.push(closeActionButton);
    }
}

function setUpPageEventListeners() {
    if (!isLoggedIn) {
        loginForm.addEventListener("submit", function (e) {
            e.preventDefault();

            var email = loginEmailTextField.value.trim();
            var emailErrorMessage = "Enter a valid username!";
            var httpErrorMessage = "Could not reach the server at this time. You can try again later.";
            const password = loginPasswordTextField.value.trim();
            const passwordErrorMessage = "A password must be at least 8 characters in length.";

            if (validateEmail(email)) {
                if (validatePassword(password)) {
                    let formData = new FormData(this);
                    let options = {
                        method: "POST",
                        body: formData
                    };

                    showUserRegisterButton.setAttribute("disabled", "");
                    loginEmailTextField.setAttribute("disabled", "");
                    loginPasswordTextField.setAttribute("disabled", "");
                    loginSubmitButton.setAttribute("disabled", "");
                    fetch(loginForm.action, options)
                        .then(response => {
                            if (response.status != 302 && response.status != 200) {
                                return response.json();
                            }

                            window.location.href = response.url;
                            return null;
                        })
                        .then(data => {
                            if (data && data["error"]) {
                                const error = data["error"];
                                const code = error["error_code"];
                                const message = error["error_message"];

                                showUserRegisterButton.removeAttribute("disabled", "");
                                loginEmailTextField.removeAttribute("disabled");
                                loginPasswordTextField.removeAttribute("disabled");
                                loginSubmitButton.removeAttribute("disabled");
                                alert(message);
                                console.error(`Error ${code}: ${message}`);
                            }
                        })
                        .catch(error => {
                            // Handle any network errors.
                            showUserRegisterButton.removeAttribute("disabled", "");
                            loginEmailTextField.removeAttribute("disabled");
                            loginPasswordTextField.removeAttribute("disabled");
                            loginSubmitButton.removeAttribute("disabled");
                            alert(httpErrorMessage);
                            console.error("There was a problem with the request:", error);
                        });
                } else {
                    loginPasswordTextField.focus();
                    alert(passwordErrorMessage);
                }
            } else {
                loginEmailTextField.focus();
                alert(emailErrorMessage);
            }
        });

        navLoginButton.addEventListener("click", () => {
            presentWindow(loginWindow);
        });

        navUserRegistrationButton.addEventListener("click", () => {
            presentWindow(userRegistrationWindow);
        });

        showLoginButton.addEventListener("click", () => {
            presentWindow(loginWindow);
        });

        showUserRegisterButton.addEventListener("click", () => {
            presentWindow(userRegistrationWindow);
        });

        userRegistrationForm.addEventListener("submit", function (e) {
            e.preventDefault();

            var email = userRegistrationEmailTextField.value.trim();
            email = email.replace(/[\x00-\x1F\x7F-\x9F]/g, "");
            const emailErrorMessage = "Enter a valid email address!";
            const httpErrorMessage = "Could not reach the server at this time. You can try again later.";
            const password = userRegistrationPasswordTextField.value;
            const passwordErrorMessage = "A password must be at least 8 characters in length.";

            if (validateEmail(email)) {
                if (validatePassword(password)) {
                    let formData = new FormData(this);
                    let options = {
                        method: "POST",
                        body: formData
                    };

                    showLoginButton.setAttribute("disabled", "");
                    userRegistrationEmailTextField.setAttribute("disabled", "");
                    userRegistrationPasswordTextField.setAttribute("disabled", "");
                    userRegistrationSubmitButton.setAttribute("disabled", "");
                    fetch(userRegistrationForm.action, options)
                        .then(response => {
                            if (response.status != 302 && response.status != 200) {
                                return response.json();
                            }

                            window.location.href = response.url;
                            return null;
                        })
                        .then(data => {
                            if (data && data["error"]) {
                                const error = data["error"];
                                const code = error["error_code"];
                                const message = error["error_message"];

                                showLoginButton.removeAttribute("disabled", "");
                                userRegistrationEmailTextField.removeAttribute("disabled", "");
                                userRegistrationPasswordTextField.removeAttribute("disabled");
                                userRegistrationSubmitButton.removeAttribute("disabled");
                                alert(message);
                                console.error(`Error ${code}: ${message}`);
                            }
                        })
                        .catch(error => {
                            // Handle any network errors.
                            showLoginButton.removeAttribute("disabled", "");
                            userRegistrationEmailTextField.removeAttribute("disabled");
                            userRegistrationPasswordTextField.removeAttribute("disabled");
                            userRegistrationSubmitButton.removeAttribute("disabled");
                            alert(httpErrorMessage);
                            console.error("There was a problem with the request:", error);
                        });
                } else {
                    userRegistrationPasswordTextField.focus();
                    alert(passwordErrorMessage);
                }
            } else {
                userRegistrationEmailTextField.focus();
                alert(emailErrorMessage);
            }
        });

        windowLayer.addEventListener("click", function (e) {
            var clickedWindow = null;
            var element = e.target;
            const windowClassName = "window";

            if (!element.classList.contains(windowClassName)) {
                while (element.parentNode) {
                    if (element.classList.contains(windowClassName)) {
                        clickedWindow = element;
                        break;
                    }

                    element = element.parentNode;
                }
            } else {
                clickedWindow = element;
            }

            if (!clickedWindow) {
                var windows = windowLayer.getElementsByClassName(windowClassName);

                for (var window of windows) {
                    window.classList.add("inactive");
                }
            } else {
                clickedWindow.classList.remove("inactive");
            }
        });
    }

    for (const button of windowActionCloseButtons) {
        button.addEventListener("click", function (e) {
            const window = getWindowForActionButton(e.target);
            dismissWindow(window);
        });
    }
}

function validateEmail(email) {
    if (email) {
        const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/i;
        return re.test(email);
    }

    return false;
}

function validatePassword(password) {
    if (password && password.length >= 8) {
        return true;
    }

    return false;
}
