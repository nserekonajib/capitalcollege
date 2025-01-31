function checkStatus() {
    fetch('/check_status')
    .then(response => response.json())
    .then(data => {
        if (data.status === "logout") {
            //alert("Your account has been deactivated. You will be logged out.");
            window.location.href = "/student_login";
        }
    });
}

setInterval(checkStatus, 5000);  // Check every 5 seconds