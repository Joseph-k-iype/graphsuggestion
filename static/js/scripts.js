document.addEventListener('DOMContentLoaded', function () {
    // No need for the cytoscape-cola plugin, using the built-in cose layout

    // Fetch dynamic data (companies and factors) from the backend
    fetch('/get_factors')
        .then(response => response.json())
        .then(data => {
            populateCompanyDropdown(data.companies);
            populateFactorOptions(data.factors, data.factor_info);
        });

    // Populate the company dropdown
    function populateCompanyDropdown(companies) {
        const companySelect = document.getElementById('companySelect');
        companySelect.innerHTML = '';  // Clear any existing options
        companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company;
            option.textContent = company;
            companySelect.appendChild(option);
        });
    }

    // Populate factor checkboxes and input fields
    function populateFactorOptions(factors, factorInfo) {
        const factorOptionsDiv = document.getElementById('factorOptions');
        factorOptionsDiv.innerHTML = '';  // Clear any existing options

        factors.forEach(factor => {
            // Create checkbox
            const checkboxDiv = document.createElement('div');
            checkboxDiv.classList.add('form-check');

            const checkbox = document.createElement('input');
            checkbox.classList.add('form-check-input');
            checkbox.type = 'checkbox';
            checkbox.value = factor;
            checkbox.id = factor;
            checkbox.onchange = () => toggleInput(factor + 'Input');

            const label = document.createElement('label');
            label.classList.add('form-check-label');
            label.htmlFor = factor;
            label.textContent = factorInfo[factor];

            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(label);

            // Create input field for threshold (optional)
            const input = document.createElement('input');
            input.type = 'number';
            input.id = factor + 'Input';
            input.classList.add('form-control', 'mt-2');
            input.placeholder = 'Minimum ' + factorInfo[factor];
            input.style.display = 'none';  // Hidden by default

            factorOptionsDiv.appendChild(checkboxDiv);
            factorOptionsDiv.appendChild(input);
        });
    }

    // Toggle visibility of the input field for the threshold
    function toggleInput(inputId) {
        const input = document.getElementById(inputId);
        if (input.style.display === "none") {
            input.style.display = "block";
        } else {
            input.style.display = "none";
        }
    }

    // Handle the recommendation button click
    document.getElementById('getRecommendations').addEventListener('click', function () {
        let company = document.getElementById('companySelect').value;

        // Get selected factors and thresholds
        let selectedFactors = [];
        let thresholds = {};

        const factorOptionsDiv = document.getElementById('factorOptions');
        factorOptionsDiv.querySelectorAll('.form-check-input').forEach(factorCheckbox => {
            if (factorCheckbox.checked) {
                selectedFactors.push(factorCheckbox.value);
                const thresholdValue = document.getElementById(factorCheckbox.value + 'Input')?.value;
                if (thresholdValue) {
                    thresholds[factorCheckbox.value] = parseFloat(thresholdValue);
                }
            }
        });

        // Send data to backend via fetch
        fetch(`/suggest_partners_dynamic`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company: company,
                factors: selectedFactors,
                thresholds: thresholds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                loadCytoscape(data);
                displayRecommendations(data.recommendations);
            }
        })
        .catch(error => {
            console.error('Error fetching recommendations:', error);
        });
    });

    // Load Cytoscape graph with the cose layout
    function loadCytoscape(data) {
        const cyContainer = document.getElementById('cy');
        cyContainer.innerHTML = '';  // Clear previous graph

        let cy = cytoscape({
            container: cyContainer,
            elements: [...data.nodes, ...data.edges],
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#007bff',
                        'border-width': 3,
                        'border-color': '#ffffff',
                        'width': 40,
                        'height': 40,
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'text-outline-width': 2,
                        'text-outline-color': '#007bff'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 3,
                        'line-color': '#aaa',
                        'target-arrow-color': '#aaa',
                        'target-arrow-shape': 'triangle',
                        'label': 'data(label)',  // This shows the distance as an edge label
                        'font-size': '12px',
                        'color': '#333'
                    }
                },
                {
                    selector: 'node:hover',
                    style: {
                        'border-width': 6,
                        'border-color': '#ffcc00',
                        'width': 60,
                        'height': 60
                    }
                }
            ],
            layout: {
                name: 'cose',  // Use the built-in cose layout
                nodeSpacing: 100,  // Increase space between nodes
                avoidOverlap: true,
                animate: true
            },
            motionBlur: true,
            wheelSensitivity: 0.1,
            boxSelectionEnabled: false,
        });

        // Event listener for node clicks
        cy.on('tap', 'node', function (event) {
            const node = event.target;
            alert('Clicked on ' + node.data('label'));
        });
    }

    // Display recommendations ranked by score
    function displayRecommendations(recommendations) {
        let recommendationDiv = document.getElementById('recommendation-list');
        recommendationDiv.innerHTML = '';  // Clear previous recommendations

        if (recommendations.length === 0) {
            recommendationDiv.innerHTML = '<p>No recommendations found for the selected factors.</p>';
        } else {
            recommendations.forEach(item => {
                recommendationDiv.innerHTML += `
                    <p>
                        <strong>Company:</strong> ${item.company} <br>
                        <strong>Stock Price:</strong> ${item['Stock Price']} <br>
                        <strong>ESG Score:</strong> ${item['ESG Score']} <br>
                        <strong>Governance Score:</strong> ${item['Governance Score']} <br>
                        <strong>Risk Level:</strong> ${item['Risk Level']} <br>
                        <strong>Market Cap:</strong> ${item['Market Cap']} <br>
                        <strong>Total Score (Closeness):</strong> ${item['Total Score']}
                    </p>
                `;
            });
        }
    }
});
