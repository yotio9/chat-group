
document.addEventListener("DOMContentLoaded", () => {

    // Menu mobile
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.querySelector(".nav-links");

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", () => {
            navLinks.classList.toggle("active");
        });

        navLinks.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("active");
            });
        });
    }

    // Interaction de démonstration dans la maquette
    const sendButton = document.querySelector(".chat-input button");

    if (sendButton) {
        sendButton.addEventListener("click", () => {
            alert("Ceci est un aperçu de la messagerie. Connectez-vous pour discuter.");
        });
    }

});
