document.addEventListener("DOMContentLoaded", function() {

    // Save edited transcription
    document.querySelectorAll(".save-btn").forEach(function(button) {
        button.addEventListener("click", function() {
            const row = button.closest("tr");
            const id = row.getAttribute("data-id");
            const correctedCell = row.querySelector(".editable");
            const correctedText = correctedCell.textContent;
        });
    });

});
