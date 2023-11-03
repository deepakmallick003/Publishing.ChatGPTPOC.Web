const inputText = document.getElementById("message");
const chatLog = document.getElementById("chat-log");

const gptNormalControl = document.getElementById("gpt-normal");
const evaResponseControl = document.getElementById("eva-output");
const evaLinksControl = document.getElementById("eva-links");
const responseSections = document.getElementById("section_2");


//const socket = io.connect('http://localhost:5000');
//const socket = io.connect(window.location.protocol + "//" + window.location.host, { path: '/socket.io' });
let socket = null;
if(USE_WEB_SOCKET === 'true'){
    socket = io.connect(window.location.protocol + "//" + window.location.host, { path: BASE_PATH + '/socket.io' });
}

// Send message on enter key press
inputText.addEventListener("keydown", (event) => {
    if (event.keyCode === 13 && !event.shiftKey) {
        event.preventDefault();
        const message = inputText.value.trim();
        $('#user-question').text(message);
        SendRequestToServer(message);
    }
});

$('#switchLinkBehaviour').on('change', function() {
    if ($(this).prop('checked')) {
        $('label[for="switchLinkBehaviour"]').text('Enable Links');
        activateInteractiveMode();
    } else {
        $('label[for="switchLinkBehaviour"]').text('Filter Graph');
        deactivateInteractiveMode();
    }
});



$(".example-questions").on("click", function(event) {
    event.preventDefault();
    const message = $(this).find('p.text-white').text().trim();
    $('#user-question').text(message);
    SendRequestToServer(message)
});

function SendRequestToServer(text) {  
    $("#report-container").empty();
    $(responseSections).show()
    $(gptNormalControl).html('');
    $(evaResponseControl).html('');
    $(evaLinksControl).html('');    

    showLoader();
    inputText.value = "";
    inputText.focus();

    if(USE_WEB_SOCKET === 'true'){
        const fd = new FormData();
        fd.append("text", text);
        get_model_response_socket(fd)
    }
    else{        
        // const fdGptNormal = new FormData();
        // fdGptNormal.append("text", text);
        // fdGptNormal.append("type", "gptnormal");  
        // get_model_response_ajax(fdGptNormal)
        
        // const fdAnswer = new FormData();
        // fdAnswer.append("text", text);
        // fdAnswer.append("type", "answer");  
        // get_model_response_ajax(fdAnswer)
        
        // const fdReference = new FormData();
        // fdReference.append("text", text);
        // fdReference.append("type", "reference");  
        // get_model_response_ajax(fdReference)

        get_model_response_sse("answer", text)
        // get_model_response_sse("reference", text)
        get_model_response_sse("gptnormal", text)
    }
}

function get_model_response_ajax(fd)
{
    $.ajax({
        url: BASE_PATH+ '/get_model_response',
        type: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.status === "full response complete") 
            {                
                if(response.type=='answer')
                {
                    $(evaResponseControl).html(response.text);
                    let filterURIParameter = extractLinks(response.text);
                    if (filterURIParameter) {
                        showRelationsReport(filterURIParameter);
                    }
                }
                else if(response.type=='reference')
                {
                    $(evaLinksControl).html(response.text);
                }
                else if(response.type=='gptnormal')
                {
                    $(gptNormalControl).html(response.text);
                }
                
            }
            else if (response.status === 'error')  {
                console.log(`error loading response for Type ${response.type}:`, response.text);
            }

            hideLoader(response.type);
        },
        error: function(xhr) {
            console.log(`error occurred:`, xhr.responseText);
        }
    });
}

function get_model_response_socket(fd)
{
    let text = fd.get('text');
    let incompleteMessageGPTNormal = "";
    let incompleteMessageAnswer = "";
    let incompleteMessageReference = "";
    $(gptNormalControl).html('');
    $(evaResponseControl).html('');
    $(evaLinksControl).html('');

    socket.emit('get_normal_request', { text: text });
    socket.emit('get_answer_request', { text: text });
    socket.emit('get_reference_request', { text: text });
    
    // Remove the previous listener
    socket.off('answer_response');  
    socket.off('reference_response');  
    socket.off('gptnormal_response');
    
    socket.on('answer_response', function(response) {
        if (response.status === 'full response complete') {
            hideLoader('answer');
            let filterURIParameter = extractLinks(incompleteMessageAnswer);
            if (filterURIParameter) {
                showRelationsReport(filterURIParameter);
            }
        } else {
            incompleteMessageAnswer += response.text;
            $(evaResponseControl).html(incompleteMessageAnswer);
        }
    });
    
    socket.on('reference_response', function(response) {
        if (response.status === 'full response complete') {
            hideLoader('reference');
        } else {
            incompleteMessageReference += response.text;
            $(evaLinksControl).html(incompleteMessageReference);
        }
    });

    socket.on('gptnormal_response', function(response) {
        if (response.status === 'full response complete') {
            hideLoader('gptnormal');            
        } else {
            incompleteMessageGPTNormal += response.text;
            $(gptNormalControl).html(incompleteMessageGPTNormal);
        }
    });

}


function get_model_response_sse(type, text) {
    let currentEventSource = null;
    let incompleteMessageGPTNormal = "";
    let incompleteMessageAnswer = "";
    let incompleteMessageReference = "";
    $(gptNormalControl).html('');
    $(evaResponseControl).html('');
    $(evaLinksControl).html('');

    // Close the existing connection, if any
    if (currentEventSource !== null) {
        currentEventSource.close();
    }

    currentEventSource = new EventSource(`${BASE_PATH}/get_model_response_sse?type=${type}&text=${text}`);

    // Define a callback for messages of type 'gptnormal'
    currentEventSource.addEventListener('gptnormal', function(event) {     
        const eventData = JSON.parse(event.data);
        if(eventData.status === 'complete') {
            hideLoader('gptnormal');
            currentEventSource.close();
        }
        else{
            incompleteMessageGPTNormal += eventData.response;
            $(gptNormalControl).html(incompleteMessageGPTNormal);
        }
    });

    // Define a callback for messages of type 'answer'
    currentEventSource.addEventListener('answer', function(event) {
        const eventData = JSON.parse(event.data);
        if(eventData.status === 'complete') {
            currentEventSource.close();
            
            rectifyResponse(incompleteMessageAnswer, send_report_data=true)
            hideLoader('answer');
            $('#switchLinkBehaviourParent').attr('style', 'display: flex !important');
            hideLoader('report')
        } else {
            incompleteMessageAnswer += eventData.response;
            $(evaResponseControl).html(incompleteMessageAnswer);
        }
    });

    // // Define a callback for messages of type 'reference'
    // currentEventSource.addEventListener('reference', function(event) {
    //     const eventData = JSON.parse(event.data);
    //     if(eventData.status === 'complete') {
    //         hideLoader('reference');
    //         currentEventSource.close();
    //     }
    //     else{
    //         incompleteMessageReference += eventData.response;
    //         $(evaLinksControl).html(incompleteMessageReference);
    //     }
    // });
}





function showLoader() {
    $('.loader').remove();
    var loaderHTML = '<div class="loader"></div>';
    $('#gpt-normal-parent').append(loaderHTML);
    $('#eva-output-parent').append(loaderHTML);
    $('#eva-links-parent').append(loaderHTML);
    $('#report-container-parent').append(loaderHTML);
}

function hideLoader(type) {
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
            $('.loader').remove();
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
        url: BASE_PATH + "/getrelationsreport",
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

function rectifyResponse(text, send_report_data=false)
{
    $(responseSections).show()
   
    const fd = new FormData();
    fd.append("text", text);
    fd.append("send_report_data", send_report_data);

    $.ajax({
        url: BASE_PATH + "/validatelinks",
        type: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function (response) {
            $(evaResponseControl).html(response.text);
            $(evaResponseControl).find("a").attr("target", "_blank");
            if(response.report_data)
            {
                processGraphData(response.report_data)
            }
        },
        error: function (err) {
          
        }
    });
}


let fdg_data, fdg_width, fdg_height, fdg_svg, fdg_zoomBehavior, fdg_zoom_scale;

function processGraphData(report_data)
{
    $('#report-container').show();

    var nodesData = [];
    var linksData = [];
    var nodeSet = new Set();

    report_data.forEach(function(item) {
        if (!nodeSet.has(item.node.title)) {
            nodesData.push({
                id: item.node.source,
                title: item.node.title,
                document_type: item.node.document_type
            });
            nodeSet.add(item.node.title);
        }
        if (item.connected_node && !nodeSet.has(item.connected_node.title)) {
            nodesData.push({
                id: item.connected_node.source,
                title: item.connected_node.title,
                document_type: item.connected_node.document_type 
            });
            nodeSet.add(item.connected_node.title);
        }

        if (item.relation && item.connected_node) {
            linksData.push({
                source: item.node.source,
                target: item.connected_node.source,
                relation: item.relation.type
            });
        }
    });

    fdg_data = {
        nodes: nodesData,  
        links: linksData,  
    };

   
    createForcedDirectedGraph(fdg_data);

}

function createForcedDirectedGraph(data) {
    const container = d3.select("#report-container");

    // Get dimensions
    fdg_width = container.node().offsetWidth;
    fdg_height = container.node().offsetHeight;

    const color = d3.scaleOrdinal(d3.schemeCategory10);

    const links = data.links.map(d => ({...d}));
    const nodes = data.nodes.map(d => ({...d}));

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id))
        .force("charge", d3.forceManyBody())
        .force("x", d3.forceX())
        .force("y", d3.forceY());

    fdg_svg = d3.select("#report-container").append("svg")
        .attr("width", fdg_width)
        .attr("height", fdg_height)
        .attr("viewBox", [-fdg_width / 2, -fdg_height / 2, fdg_width, fdg_height])
        .attr("style", "max-width: 100%; height: auto;");

    const g = fdg_svg.append("g");  // Main group element

    const link = g.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.sqrt(d.value));

    const node = g.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 0.3)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        // .attr("stroke", d => d.document_type === "article" ? "rgb(60, 60, 67)" : "hsl(20 85% 57%)" )
        .attr("r", d => d.document_type === "article" ? 10 : 5)  // Articles are bigger, adjust sizes as needed
        .attr("fill", d => {
            if (d.document_type === "article") {
                return "hsl(20 85% 57%)";  // Color for articles
            } else if (d.document_type === "concept") {
                return "rgb(60, 60, 67)";  // Color for concepts
            } else {
                return color(d.group);  // Default color
            }
        });

    const labels = g.append("g")
    .selectAll("text")
    .data(nodes)
    .join("text")
    .text(d => d.title)
    .attr("font-size", "1.5px") 
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "middle")
    .attr("fill", d => d.document_type === "concept" ? "#ccc" : "#000")
    .style("cursor", "default");  
    
    const edgeLabels = g.append("g")
    .selectAll("text")
    .data(links)
    .join("text")
    .text(d => d.relation)
    .attr("font-size", "0.7px")
    .style("cursor", "default");;

    // Zoom behavior
    fdg_zoomBehavior = d3.zoom()
        .scaleExtent([0.5, 20])  // Adjust as needed
        .on("zoom", (event) => {
            g.attr("transform", event.transform);
            fdg_zoom_scale = event.transform.k;
        })
        .on("end", () => {
            // setTimeout(resetGraphPosition, 2000);  // Wait for 2 seconds (2000ms) before resetting
        });

    fdg_svg.call(fdg_zoomBehavior);
    const initialTransform = d3.zoomIdentity.translate(0, 0).scale(2);
    fdg_svg.call(fdg_zoomBehavior.transform, initialTransform);

    node.append("title")
        .text(d => d.title);

    node.call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));

    simulation.on("tick", () => {      
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        labels
            .attr("x", d => d.x)
            .attr("y", d => d.y);

        edgeLabels
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2)
            .attr("text-anchor", "middle");

        // Update global fdg_data.nodes with current positions
        if(nodes.length>0){
            for (let i = 0; i < fdg_data.nodes.length; i++) {
                if(nodes[i]){
                    fdg_data.nodes[i].x = nodes[i].x;
                    fdg_data.nodes[i].y = nodes[i].y;
                }
            }
        }
    });
  
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }

    function resetGraphPosition() {
        fdg_svg.transition()
            .duration(750)
            .call(fdg_zoomBehavior.transform, d3.zoomIdentity.translate(0, 0).scale(2));
    }
}


function activateInteractiveMode() {
    $('#eva-output a').each(function() {
        let nodeId = $(this).attr('href');
        $(this).removeAttr('href')
            .data('originalHref', nodeId)
            .addClass('interactive-link')
            .off('click')  // To ensure there's no duplicate event binding
            .on('click', function(e) {
                e.preventDefault();  // Prevent the default link behavior
              
                const nodeData = fdg_data.nodes.find(d => d.id === nodeId);
                if (nodeData) {
                    $('#report-container').focus();
                    zoomIntoNode(nodeData);
                }
            });
    });
}

function deactivateInteractiveMode() {
    $('.interactive-link').each(function() {
        $(this).attr('href', $(this).data('originalHref'))
            .removeClass('interactive-link')
            .off('click');  // Remove the click event listener
    });
}

function zoomIntoNode(d) {
    let scale = 15;
    // Initial translation to bring node to bottom right
    let tx = fdg_width*0.5 - scale*d.x;
    let ty = fdg_height*0.5 - scale*d.y;

    // Corrective translation to shift node to center
    tx -= fdg_width*0.50;
    ty -= fdg_height*0.50;

    fdg_svg.transition()
        .duration(750)
        .call(fdg_zoomBehavior.transform,
            d3.zoomIdentity
                .translate(tx, ty)
                .scale(scale)
        );
}




// text = 'A global health risk framework could potentially mitigate the impact of future outbreaks of diseases like <a href="https://id.cabi.org/cabt/301097">Ebola haemorrhagic fever</a> by facilitating the study of disease transmission, diagnosis, and proper containment of the ill. It could also aid in vaccine development. This framework would be crucial in the event of another Ebola-like disease outbreak. It could also be beneficial in the context of international collaboration, which is critical for tackling the emerging challenges of various diseases. The potential areas of cooperation could include biomedical and health research such as advanced capacity in genomics, proteomics, and modern biology, as well as the establishment of public and private clinical services. The strength of certain countries in areas like generic drugs, vaccine supply, open source drug discovery, and development could be vital for improving the healthcare sector in other countries. Targeted intervention in disease prevention and mitigation could contribute significantly to the provision of healthcare services. Entrepreneurship platforms, incubators, product development partnerships, early stage development R&amp;D, and similar innovative health strategies could lift the burden of diseases.<br><h5>Source Articles</h5><ul><li><a href="https://www.cabidigitallibrary.org/doi/10.5555/20183000178">The ebola epidemic in West Africa: proceedings of a workshop</a></li><li><a href="https://www.cabidigitallibrary.org/doi/10.5555/20183026231">Health sector cooperation in Asia Africa Growth Corridor</a></li></ul>'
// rectifyResponse(text)