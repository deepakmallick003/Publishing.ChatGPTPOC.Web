const inputText = document.getElementById("message");
const evaResponseControl = document.getElementById("eva-answer");
const evaReferenceControl = document.getElementById("eva-reference");
const responseSections = document.getElementById("section_2");
const cabtBaseUri = "https://id.cabi.org/cabt/"
const cabidigitallibraryBaseUri = "https://www.cabidigitallibrary.org/doi/10.5555/"
let answerEventSource;
let referenceEventSource;
let globalConceptsDict = {};
let incompleteSummary = "";


$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();

    $('.model-parameters-sliders').on('input', function () {
        var sliderValue = $(this).val();
        $(this).closest('.form-group').find('.model-parameters-value').text(sliderValue);
        $(this).val(sliderValue);  // This line may not be necessary as the slider value is what triggered this event.
    });
});

// Send message on enter key press
inputText.addEventListener("keydown", (event) => {
    if (event.keyCode === 13 && !event.shiftKey) {
        event.preventDefault();
        const message = inputText.value.trim();
        $('#user-question').text(message);
        SendRequestToServer(message);
    }
});

window.addEventListener("beforeunload", function() {
    closeSSE()
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

function checkAuthentication() {
    
    var uniqueSSESessionId='';
    
    $.ajax({
        url: '/get_user_oid',
        async: false,
        method: 'GET',
        success: function(response) {
            uniqueSSESessionId = `${response.oid}_${new Date().getTime()}`;
        },
        error: function(xhr) {
            if (xhr.status === 401) {
                window.location.href = xhr.responseJSON.auth_url;
            }
        }
    });

    return uniqueSSESessionId
}

function SendRequestToServer(text) {  
    $("#report-container").empty();
    $(responseSections).show()
    $(evaResponseControl).html('');
    
    showLoader();
    inputText.value = "";
    // inputText.focus();
           
    uniqueSSESessionId = checkAuthentication();
    if (uniqueSSESessionId!=''){
        startSSE(text, uniqueSSESessionId);
    }
}

function closeSSE(){
    if (answerEventSource !== undefined && answerEventSource !== null) {
        answerEventSource.close();
        answerEventSource = null;
    }
}

function startSSE(text, uniqueSSESessionId) {
    closeSSE()
    let answerEventSource = null;
    let extractedPANS = [];
    incompleteSummary = "";
    globalConceptsDict = {};
    $(evaResponseControl).html('');
    $(evaReferenceControl).html('');

    var temperature = $('#temperSlider').val();
    var frequency_penalty = $('#freqPenSlider').val();
    var presence_penalty = $('#presPenSlider').val();

    answerEventSource = new EventSource(`${BASE_PATH}/get_answer_sse?text=${text}&temperature=${temperature}&frequency_penalty=${frequency_penalty}&presence_penalty=${presence_penalty}&sessionId=${uniqueSSESessionId}`);

    answerEventSource.addEventListener('llmstream', function(event) {
        const eventData = JSON.parse(event.data);
        if(eventData.sessionId === uniqueSSESessionId){
            if(eventData.status === 'complete') {
                answerEventSource.close();
                hideLoader('answer');
                fetchAndUpdateConceptDict()
                populateTextWithConcepts()
                fetchSourcesAndPopulate(extractedPANS)
            } else {
                incompleteSummary += eventData.response;
                $(evaResponseControl).html(incompleteSummary);

                fetchAndUpdateConceptDict()
                if(extractedPANS.length==0){
                    extractedPANS = extractPANSFromSummary()
                }
            }
        }
        else{
            answerEventSource.close();
        }
    });

    answerEventSource.addEventListener('error', function(event) {
        debugger;
        const errorData = JSON.parse(event.data);
        if(errorData.sessionId === uniqueSSESessionId){            
            answerEventSource.close();
            hideLoader('answer');
            hideLoader('reference');
            console.error(errorData.message);
            showPopUp('Error', errorData.message)
        }
    });
}

function extractPANSFromSummary() {
    let extractedSources = [];
    const sourceTagPattern = /<sources>(.*?)<\/sources>/gs;
    const matches = [...incompleteSummary.matchAll(sourceTagPattern)];
    matches.forEach(match => {
        // Split by new line or comma followed by optional whitespace
        const pans = match[1].split(/\s*,\s*|\n+/).filter(pan => pan.match(/^\d+$/));
        extractedSources.push(...pans);
    });
    return extractedSources;
}


// Tracks sentences that have been processed
let lastSentences = new Set(); 
function fetchAndUpdateConceptDict() {
    let parser = new DOMParser();
    let doc = parser.parseFromString(incompleteSummary, 'text/html');
    let paragraphs = doc.querySelectorAll('p');
    let allText = Array.from(paragraphs).map(p => p.textContent).join(' ');
    
    // Split the text into sentences. This simple split might need refinement for more complex text structures.
    let sentences = allText.match(/[^.!?]+[.!?]/g) || [];

    // Find new sentences that haven't been processed
    let newSentences = sentences.filter(sentence => !lastSentences.has(sentence.trim()));
    
    // Process each new sentence sequentially
    newSentences.forEach(sentence => {
        if (sentence.trim()) {
            lastSentences.add(sentence.trim()); // Mark this sentence as processed

            const fd = new FormData();
            fd.append("text", sentence);

            $.ajax({
                url: BASE_PATH + "/fetchconcepts",
                type: "POST",
                data: fd,
                processData: false,
                contentType: false,
                success: function (response) {
                    Object.assign(globalConceptsDict, response.concepts);
                    populateTextWithConcepts();
                },
                error: function (err) {
                    // Handle error
                }
            });
        }
    });
}


function populateTextWithConcepts() {

    // Iterate through the global concepts dictionary
    Object.keys(globalConceptsDict).forEach(concept => {
        const conceptSource = globalConceptsDict[concept];
        const anchorTag = `<a href="${cabtBaseUri + conceptSource}" target="_blank">${concept}</a>`;
        const escapedConcept = concept.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const regex = new RegExp(escapedConcept, 'g');

        incompleteSummary = incompleteSummary.replace(regex, anchorTag);
    });

    $(evaResponseControl).html(incompleteSummary);
}


function fetchSourcesAndPopulate(pans)
{
    checkAuthentication();
    const fd = new FormData();
    fd.append("pans", pans.join(','));

    $.ajax({
        url: BASE_PATH + "/fetchsources",
        type: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function (response) {
            populateSources(response.sources)
        },
        error: function (err) {
        }
    });
}

function populateSources(sources){
    var $template = $('#reference-template').clone().removeAttr('id').show(); // Clone and prepare the template

    sources.forEach(function(source) {
        // Clone the template for each source
        var $reference = $template.clone(); 
        // Populate the cloned template with source data
        $reference.find('.title-text').text(source['Title']);
        $reference.find('.title-text').attr('title', source['Title']);
        $reference.find('.title-anchor').attr('href', cabidigitallibraryBaseUri + source['PAN']);
        $reference.find('.publisher').append(source['Publisher Name'] + ', ' + source['Publishing Date']);
        source['Authors'].forEach(function(author) {
            var badge = $('<span></span>')
                .addClass('badge bg-secondary')
                .text(author);
            $reference.find('.authors').append(badge);
        });
        
        $reference.find('.location').append(source['Publisher Location']);
        $reference.find('.summary-text').text(source['Abstract Summary']);

        // Append the populated template to the container
        $(evaReferenceControl).append($reference);
    });

    $('.toggle-summary').on('click', function() {
        $('.summary-text').not($(this).closest('.card').find('.summary-text')).slideUp();
        $(this).closest('.card').find('.summary-text').slideToggle(function() {
            if ($(this).is(':visible')) {
                $('.toggle-summary').text('Show Summary');
                $(this).closest('.card').find('.toggle-summary').text('Hide Summary');
            } else {
                $(this).closest('.card').find('.toggle-summary').text('Show Summary');
            }
        });
    });

    hideLoader('reference');
}


function showLoader() {
   $('.loader').remove();
   var loaderHTML = '<div class="loader"></div>';
   $('#eva-answer-parent').append(loaderHTML);
   $('#eva-reference-parent').append(loaderHTML);
   // $('#report-container-parent').append(loaderHTML);
}

function hideLoader(type) {
   switch(type)
   {
       case 'answer':
           $('#eva-answer-parent').find('.loader').remove();
           break;
       case 'reference':
               $('#eva-reference-parent').find('.loader').remove();
               break;
       case 'report':
           $('#report-container-parent').find('.loader').remove();
           break;
       default:
           $('.loader').remove();
   }
}

function showPopUp(title, message) {
    $('#genericModalLabel').text(title);  // Set the title
    $('#genericModalBody').text(message);  // Set the message
    $('#genericModal').modal('show');  // Show the modal

    // setTimeout(function () {
    //     $('#genericModal').modal('hide');
    // }, 3000);
}

function rectifyResponse(text, send_report_data=false)
{
    checkAuthentication();

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
                document_type: item.node.type
            });
            nodeSet.add(item.node.title);
        }
        if (item.connected_node && !nodeSet.has(item.connected_node.title)) {
            nodesData.push({
                id: item.connected_node.source,
                title: item.connected_node.title,
                document_type: item.connected_node.type 
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
        // .attr("stroke", d => d.type === "article" ? "rgb(60, 60, 67)" : "hsl(20 85% 57%)" )
        .attr("r", d => d.type === "article" ? 10 : 5)  // Articles are bigger, adjust sizes as needed
        .attr("fill", d => {
            if (d.type === "article") {
                return "hsl(20 85% 57%)";  // Color for articles
            } else if (d.type === "concept") {
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
    .attr("fill", d => d.type === "concept" ? "#ccc" : "#000")
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
    $('#eva-answer a').each(function() {
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
