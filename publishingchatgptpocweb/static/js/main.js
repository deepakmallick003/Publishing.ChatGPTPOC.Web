const inputText = document.getElementById("message");
const chatLog = document.getElementById("chat-log");

const gptNormalControl = document.getElementById("gpt-normal");
const evaResponseControl = document.getElementById("eva-output");
const evaLinksControl = document.getElementById("eva-links");
const responseSections = document.getElementById("section_2");

const sendButton = document.getElementById("send-btn");
const recordButton = document.getElementById("record-btn");
const messageForm = document.getElementById("message-form");

let recognition = null;
let mediaRecorder = null;
let audioChunks = [];

// const socket = io.connect('http://localhost:5000');
//const socket = io.connect(window.location.protocol + "//" + window.location.host, { path: BASE_PATH + '/socket.io' });
const socket = io.connect('https://development-cdn.cabi.org', { path: '/publishingchatgpt/socket.io' });

// Send message on enter key press
inputText.addEventListener("keydown", (event) => {
    if (event.keyCode === 13 && !event.shiftKey) {
        event.preventDefault();
        const message = inputText.value.trim();
        $('#user-question').text(message);
        sendMessage(message);
    }
});

$(".example-questions").on("click", function(event) {
    event.preventDefault();
    const message = $(this).find('p.text-white').text().trim();
    $('#user-question').text(message);
    sendMessage(message)
});

// Send user message to the chat log
function sendMessage(message, isAudio = false) {
    inputText.value = "";
    inputText.focus();
    $("#report-container").empty();
    // chatLog.scrollTop = chatLog.scrollHeight;

    if (recognition && recognition.recognizing) {
        recognition.stop();
        recordButton.classList.remove("active");
    }

    const fd = new FormData();
    if (isAudio) {
        fd.append("audio", message);
    } else {
        fd.append("text", message);
    }

    if ($('#audio-toggle').is(":checked")) {
        fd.append('audio_response', 'true');
    } else {
        fd.append('audio_response', 'false');
    }

     // Call SendRequestToServer with the FormData instance
    SendRequestToServer(fd)
}

let currentSection = null;
let answerText = '';
let referenceText = '';

function SendRequestToServer(fd) {
    $(responseSections).show()
    showLoader();
    let text = fd.get('text');    
    let incompleteMessageGPTNormal = "";
    let incompleteMessageAnswer = "";
    let incompleteMessageReference = "";
    $(gptNormalControl).html('');
    $(evaResponseControl).html('');
    $(evaLinksControl).html('');

    socket.emit('get_answer', { text: text });
    socket.emit('get_reference', { text: text });
    socket.emit('get_gptnormal', { text: text });

    socket.off('gptnormal_response');  // Remove the previous listener
    socket.on('gptnormal_response', function(response) {
        if (response.status === 'complete') {
            hideLoader('gptnormal');            
        } else {
            incompleteMessageGPTNormal += response;
            $(gptNormalControl).html(incompleteMessageGPTNormal);
        }
    });

    socket.off('answer_response');  // Remove the previous listener
    socket.on('answer_response', function(response) {
        if (response.status === 'complete') {
            hideLoader('answer');
            let filterURIParameter = extractLinks(incompleteMessageAnswer);
            if (filterURIParameter) {
                showRelationsReport(filterURIParameter);
            }
        } else {
            incompleteMessageAnswer += response;
            $(evaResponseControl).html(incompleteMessageAnswer);
        }
    });
    
    socket.off('reference_response');  // Remove the previous listener
    socket.on('reference_response', function(response) {
        if (response.status === 'complete') {
            hideLoader('reference');
        } else {
            incompleteMessageReference += response;
            $(evaLinksControl).html(incompleteMessageReference);
        }
    });
}


function showLoader() {
    var loaderHTML = '<div class="loader"></div>';
    $('#gpt-normal-parent').append(loaderHTML);
    $('#eva-output-parent').append(loaderHTML);
    $('#eva-links-parent').append(loaderHTML);
    $('#report-container-parent').append(loaderHTML);
    // $('#user-question').append(loaderHTML);
}

function hideLoader(type) {
    // $('.loader').remove();
    switch(type)
    {
        case 'gptnormal':
            $('#gpt-normal-parent').find('.loader').remove();
            break;
        case 'answer':
            $('#eva-output-parent').find('.loader').remove();
            break;
        case 'reference':
            $('#eva-links-parent').find('.loader').remove();
            break;
        case 'report':
            $('#report-container-parent').find('.loader').remove();
            break;
        default:
            $('#user-question').find('.loader').remove();
    }
}


function extractLinks(text) {
    // Step 1: Extract all links matching the specified patterns
    const linkPattern = /https:\/\/www\.cabidigitallibrary\.org\/doi\/10\.5555\/\d+|https:\/\/id\.cabi\.org\/cabt\/\d+/g;
    const links = text.match(linkPattern);
    
    if (!links) {
        return '';
    }
    
    // Step 2: Remove duplicate links by converting the array to a Set and then back to an array
    const uniqueLinks = [...new Set(links)];
    
    return uniqueLinks
}


function showRelationsReport(filterURIParameter)
{
    $.ajax({
        type: "GET",
        url: BASE_PATH + "getrelationsreport",
        dataType: "json",
        success: function (data) {

            var reportContainer = $("#report-container").get(0);

            try {
                // Attempt to get the existing PowerBI component
                var existingReport = powerbi.get(reportContainer);
                // If a component is retrieved, reset it to clear previous reports
                if (existingReport) {
                    powerbi.reset(reportContainer);
                }
            } catch (error) {
            }

            // Initialize iframe for embedding report
            powerbi.bootstrap(reportContainer, { type: "report" });
            var models = window["powerbi-client"].models;
            var reportLoadConfig = {
                type: "report",
                tokenType: models.TokenType.Embed,
                settings: {
                    filterPaneEnabled: false,
                    navContentPaneEnabled: false
                }
            };

            embedData = $.parseJSON(JSON.stringify(data));
            reportLoadConfig.accessToken = embedData.accessToken;
            // You can embed different reports as per your need
            reportLoadConfig.embedUrl = embedData.reportConfig[0].embedUrl;

            // Use the token expiry to regenerate Embed token for seamless end user experience
            // Refer https://aka.ms/RefreshEmbedToken
            tokenExpiry = embedData.tokenExpiry;

            // Embed Power BI report when Access token and Embed URL are available
            var report = powerbi.embed(reportContainer, reportLoadConfig);

            // // Define your filter here
            var filter = {
                $schema: "http://powerbi.com/product/schema#basic",
                target: {
                    table: "Relations",
                    column: "URI"
                },
                operator: "In",
                values: filterURIParameter // Your filter values as an array
            };

            // Triggers when a report schema is successfully loaded
            report.on("loaded", function () {
                hideLoader('report')
                console.log("Report load successful");   
                $('#report-container').show();

                // // Set the filters after the report has loaded
                report.getFilters()
                .then(filters => {
                    filters.push(filter);
                    return report.setFilters(filters);
                })
                .catch(error => {
                    console.error(error);
                });
            });

            // Triggers when a report is successfully embedded in UI
            report.on("rendered", function () {
                hideLoader('report')
                console.log("Report render successful");                
            });

            // Clear any other error handler event
            report.off("error");

            // Below patch of code is for handling errors that occur during embedding
            report.on("error", function (event) {
                hideLoader('report')
                var errorMsg = event.detail;
                // Use errorMsg variable to log error in any destination of choice
                console.error(errorMsg);
                return;
            });
        },
        error: function (err) {
            // Show error container
            // var errorContainer = $(".error-container");
            // $(".embed-container").hide();
            // errorContainer.show();

            // // Format error message
            // var errMessageHtml = "<strong> Error Details: </strong> <br/>" + $.parseJSON(err.responseText)["errorMsg"];
            // errMessageHtml = errMessageHtml.split("\n").join("<br/>")

            // // Show error message on UI
            // errorContainer.html(errMessageHtml);
        }
    });
}

// showRelationsReport(['https://www.cabidigitallibrary.org/doi/10.5555/20183000178'])