const BASE_URL = window.location.origin;

async function fetchData(apiEndpoint) {
    try {
        let response = await fetch(`${BASE_URL}${apiEndpoint}`);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${apiEndpoint}:`, error);
        return null;
    }
}

function updateCSVTable(data) {
    if (!data || data.length === 0) {
        document.getElementById("table-body").innerHTML = "<tr><td colspan='4'>No data found</td></tr>";
        return;
    }

    data = data.map(row => {
        let cleanedRow = {};
        Object.keys(row).forEach(key => {
            cleanedRow[key.trim()] = row[key];
        });
        return cleanedRow;
    });

    // let allKeys = Object.keys(data[0]);
    // let remainingKeys = allKeys.filter(key => key !== "element" && key !== "avg" && key !== "required");
    // let orderedKeys = ["element", "avg", ...remainingKeys, "required"].filter(key => allKeys.includes(key));

	let allKeys = Object.keys(data[0]);


    let flpKeys = allKeys.filter(key => /FLP/i.test(key) && key !== "element" && key !== "required");
    let llpKeys = allKeys.filter(key => /LLP/i.test(key) && key !== "element" && key !== "required");

    // Sort FLP fields by time (after the | symbol)
    flpKeys.sort((a, b) => {
        let aTime = a.split("|")[1]?.trim() || "00:00";
        let bTime = b.split("|")[1]?.trim() || "00:00";
        return aTime.localeCompare(bTime);
    });

    // Sort LLP fields by time (after the | symbol)
    llpKeys.sort((a, b) => {
        let aTime = a.split("|")[1]?.trim() || "00:00";
        let bTime = b.split("|")[1]?.trim() || "00:00";
        return aTime.localeCompare(bTime);
    });

    let orderedKeys = ["element", ...flpKeys, ...llpKeys, "required"];

    let tableHeader = document.getElementById("table-header");
    tableHeader.innerHTML = "";
    orderedKeys.forEach(key => {
        let th = document.createElement("th");
        th.textContent = key;
        tableHeader.appendChild(th);
    });

    let tableBody = document.getElementById("table-body");
    tableBody.innerHTML = "";
    data.forEach(row => {
        let tr = document.createElement("tr");

        let min = null,
            max = null;
        if (row["required"]) {
            let match = row["required"].match(/\(MIN\)([\d.]+)\s*TO\s*([\d.]+)\(MAX\)/);
            if (match) {
                min = parseFloat(match[1]);
                max = parseFloat(match[2]);
            }
        }

        orderedKeys.forEach((key) => {
            let td = document.createElement("td");
            td.textContent = row[key] !== undefined ? row[key] : "";

            if (min !== null && max !== null && !["element", "required"].includes(key)) {
                let value = parseFloat(row[key]);
                if (!isNaN(value)) {
                    if (value < min) {
                        td.style.backgroundColor = "#FF9999"; // red
                    } else if (value >= min && value <= max) {
                        td.style.backgroundColor = "lightgreen"; // green
                    } else {
                        td.style.backgroundColor = "#FFFF66"; // yellow
                    }
                    td.style.color = "black";
                }
            } else {
                td.style.backgroundColor = "rgba(240, 240, 240, 0.9)";
                if (key !== "element") td.style.color = "black";
            }

            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });
}

async function loadData(dataEndpoint) {
    let tableData = await fetchData(dataEndpoint);
    if (tableData) updateCSVTable(tableData);
}

document.addEventListener("DOMContentLoaded", function() {
    let homeButton = document.getElementById("home-button");
    if (homeButton) {
        homeButton.addEventListener("click", function() {
            window.location.href = "/";
        });
    }
});