
function loadStudentData() {
    fetch('/get_student_data')
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById("table-container").innerHTML = "<p>" + data.error + "</p>";
            return;
        }

        document.getElementById("student-name").innerText = data.student_name;
        
        let tableHTML = `
            <table class="min-w-full table-auto border-collapse bg-white rounded-lg shadow-md">
                <thead class="bg-blue-500 text-white">
                    <tr>
                        <th class="px-4 py-3 text-left">Paper Number</th>
                        <th class="px-4 py-3 text-left">Paper Name</th>
                        <th class="px-4 py-3 text-left">Start Time</th>
                        <th class="px-4 py-3 text-left">Join Zoom</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.classes.forEach(cls => {
            tableHTML += `
                <tr>
                    <td class="px-4 py-3">${cls['Paper Number']}</td>
                    <td class="px-4 py-3">${cls['Paper Name']}</td>
                    <td class="px-4 py-3">${cls['Start Time']}</td>
                    <td class="px-4 py-3">
                        <a href="${cls['Zoom Link']}" target="_blank"
                        class="btn btn-primary text-white bg-blue-500 hover:bg-blue-700 rounded-md px-4 py-2">
                            Join Class
                        </a>
                    </td>
                </tr>
            `;
        });

        tableHTML += `</tbody></table>`;
        document.getElementById("table-container").innerHTML = tableHTML;
    });
}

// Refresh data every 5 seconds
setInterval(loadStudentData, 5000);
loadStudentData();  // Load data initially

