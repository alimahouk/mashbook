let chatForkForm;
let chatID = null;
let isConnected = false;
const contentMaxLen = 4097;
let messages;
let pageTitle;
let selectionPopup;
let sendUserInputButton;
let sessionID;
let shouldDisplaySelectionPopup = false;
let socket;
let userInputForm;
let userInputField;
let windowActionCloseButtons;


document.addEventListener("DOMContentLoaded", function () {
    setUpPage();
});


function connect() {
    let transports = ["websocket", "polling"]; // Use WebSocket first, if available.

    if (debug) {
        transports = ["polling"];
    }

    socket = io("/", {
        transports: transports
    });

    socket.on("connect", function () {

    });
    socket.on("disconnect", function () {
        isConnected = false;
        //alert("The connection to the server dropped. You need to refresh the page.");
    });
    socket.on("message", (data) => {
        if (data.error) {
            alert(data.error);
        } else if (data.message) {
            let newMessage = document.createElement("article");
            newMessage.setAttribute("id", data.message.id);
            newMessage.classList.add("message");
            newMessage.classList.add("system");

            let header = document.createElement("header");
            let heading = document.createElement("h3");
            heading.classList.add("author");
            heading.innerHTML = "Mashbook";
            header.appendChild(heading);

            let content = document.createElement("section");
            content.setAttribute("itemprop", "text");
            content.classList.add("content");
            content.innerHTML = data.message.content_html;

            newMessage.appendChild(header);
            newMessage.appendChild(content);
            messages.appendChild(newMessage);
            window.scrollTo(0, document.body.scrollHeight); // Scroll to bottom.
        } else if (data.session_id) {
            sessionID = data.session_id
            didConnect();
        }
    });
}

function didConnect() {
    isConnected = true;
    userInputField.removeAttribute("disabled");
    userInputField.focus();
}

function dismissWindow(window) {
    if (window) {
        window.classList.add("hidden");

        const clearableFields = window.querySelectorAll(".clearable");

        for (const field of clearableFields) {
            field.value = "";
        }
    }
}

function calculateGlobalOffset(root, range) {
    let totalOffset = 0;
    const iterateNodes = function (node) {
        if (!node) {
            return true; // Continue if the node is null or undefined
        }
        if (node === range.startContainer) {
            return false;
        }
        if (node.nodeType === Node.TEXT_NODE) {
            totalOffset += node.length;
        }
        for (let child of node.childNodes) {
            if (!iterateNodes(child)) {
                return false;
            }
        }
        return true;
    };

    iterateNodes(root);

    return totalOffset + range.startOffset;
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

        if (window) {

        }
    }

    return window;
}

function handleTextSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const commonAncestor = range.commonAncestorContainer;

        let currentElement = commonAncestor.nodeType === 3 ?
            commonAncestor.parentNode :
            commonAncestor;

        while (currentElement != null) {
            if (currentElement.tagName === "SECTION") {
                let ancestor = currentElement.closest('article.message');
                if (ancestor) {
                    const offset = calculateGlobalOffset(currentElement, range);
                    const messageID = ancestor.getAttribute("id");
                    presentSelectionPopup(range, offset, messageID, rect, selectionPopup);
                    break;
                }
            }
            currentElement = currentElement.parentElement;
        }
    }
}

function presentSelectionPopup(selectionRange, globalStartOffset, messageID, rect, popup) {
    chatForkForm.context_range_length.value = selectionRange.toString().length;
    chatForkForm.context_range_start.value = globalStartOffset;
    chatForkForm.message_id.value = messageID;
    let selectedText = selectionRange.toString().trim();

    if (selectedText.length > 340) {
        selectedText = selectedText.substr(0, 340) + "…";
    }

    selectionPopup.querySelector(".label").textContent = `"${selectedText}"`;
    selectionPopup.classList.remove("hidden"); // Temporarily display to get the height.
    const popupHeight = selectionPopup.offsetHeight;
    const popupWidth = popup.offsetWidth;

    if (window.innerWidth > 768) {
        // Position it centered above the selected text.
        const selectionMidpoint = rect.left + (rect.width / 2);
        let calculatedLeft = (selectionMidpoint - (popupWidth / 2) + window.scrollX);
        let calculatedTop = (rect.top + window.scrollY - popupHeight - 10);

        // Check for left edge.
        if (calculatedLeft < 10) {
            calculatedLeft = 10;
        }
        // Check for right edge.
        if ((calculatedLeft + popupWidth) > window.innerWidth) {
            calculatedLeft = window.innerWidth - popupWidth - 10;
        }
        // Check for top edge.
        if (calculatedTop < 10) {
            calculatedTop = 10;
        }

        selectionPopup.style.left = calculatedLeft + "px";
        selectionPopup.style.top = calculatedTop + "px";
    }
    // On smaller screens, use pure CSS to center the window in the screen regardless of where selection is.

    selectionPopup.querySelector(".autofocus").focus();

    shouldDisplaySelectionPopup = true;
}

function setUpPage() {
    setUpPageBindings();
    setUpPageEventListeners();

    connect();
    window.scrollTo(0, document.body.scrollHeight); // Scroll to bottom.
}

function setUpPageBindings() {
    chatForkForm = document.chatForkForm;
    chatID = document.querySelector("#chat").getAttribute("data-chat-id");
    messages = document.querySelector("#messages");
    pageTitle = document.querySelector("#title");
    selectionPopup = document.querySelector("#selectionPopup");
    userInputForm = document.userInputSection;
    userInputField = userInputForm.userInputField;
    sendUserInputButton = userInputForm.sendUserInputButton;

    windowActionCloseButtons = [];
    const windowActionButtons = document.querySelectorAll(".window .windowActionButtons");

    for (const buttons of windowActionButtons) {
        const closeActionButton = buttons.getElementsByClassName("close")[0];
        windowActionCloseButtons.push(closeActionButton);
    }
}

function setUpPageEventListeners() {
    chatForkForm.addEventListener("submit", (event) => {
        if (chatForkForm.content_md.value != null) {
            const prompt = chatForkForm.content_md.value.trim();

            if (prompt.length == 0) {
                event.preventDefault();
                chatForkForm.content_md.value = "";
                chatForkForm.content_md.focus();
            }
        }
    });

    // Listen to mousedown to hide the selection popup if clicking outside.
    document.addEventListener("mousedown", (event) => {
        if (shouldDisplaySelectionPopup && !selectionPopup.contains(event.target)) {
            dismissWindow(selectionPopup);
            shouldDisplaySelectionPopup = false;
        }
    });

    // Listen to mouseup to potentially show the selection popup.
    document.addEventListener("mouseup", () => {
        handleTextSelection();
    });

    // Listen to touchend for touchscreen devices.
    document.addEventListener("touchend", () => {
        handleTextSelection();
    });

    userInputField.addEventListener("input", () => {
        let userInput = userInputField.value.trim();

        if (userInput.length > 0 && isConnected) {
            sendUserInputButton.removeAttribute("disabled");
        } else {
            sendUserInputButton.setAttribute("disabled", "");
        }
    });

    userInputForm.addEventListener("submit", (event) => {
        event.preventDefault();

        if (isConnected) {
            let userInput = userInputField.value.trim();

            if (userInput.length > 0) {
                if (userInput.length > contentMaxLen - 100) {
                    alert("Your message is too long!");
                } else {
                    let newMessage = document.createElement("article");
                    newMessage.classList.add("message");
                    newMessage.classList.add("user");

                    let header = document.createElement("header");
                    let heading = document.createElement("h3");
                    heading.classList.add("author");
                    heading.innerHTML = "You";
                    header.appendChild(heading);

                    let content = document.createElement("section");
                    content.setAttribute("itemprop", "text");
                    content.classList.add("content");
                    content.innerHTML = marked.parse(userInput);

                    newMessage.appendChild(header);
                    newMessage.appendChild(content);
                    messages.appendChild(newMessage);
                    window.scrollTo(0, document.body.scrollHeight); // Scroll to bottom.

                    socket.send({
                        "chat_id": chatID,
                        "content_md": userInput
                    });

                    userInputField.value = "";
                }
            } else {
                userInputField.value = "";
            }

            userInputField.focus();
        }
    });

    for (const button of windowActionCloseButtons) {
        button.addEventListener("click", function (e) {
            const window = getWindowForActionButton(e.target);
            dismissWindow(window);
        });
    }
}
