
document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("registerForm");
    const password1 = document.getElementById("password1");
    const password2 = document.getElementById("password2");
    const passwordMessage = document.getElementById("passwordMessage");
    const strengthBar = document.getElementById("strengthBar");
    const strengthText = document.getElementById("strengthText");
    const formError = document.getElementById("formError");

    // Afficher ou masquer les mots de passe
    document.querySelectorAll(".toggle-password").forEach(button => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);

            if (!input) return;

            const isHidden = input.type === "password";

            input.type = isHidden ? "text" : "password";
            button.textContent = isHidden ? "Masquer" : "Voir";
            button.setAttribute(
                "aria-label",
                isHidden ? "Masquer le mot de passe" : "Afficher le mot de passe"
            );
        });
    });

    // Vérifier la force du mot de passe
    function checkPasswordStrength(password) {
        let score = 0;

        if (password.length >= 8) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;

        return score;
    }

    password1.addEventListener("input", () => {
        const password = password1.value;
        const score = checkPasswordStrength(password);

        const levels = [
            { width: "0%", text: "8 caractères minimum", color: "#ff7272" },
            { width: "20%", text: "Très faible", color: "#ff7272" },
            { width: "40%", text: "Faible", color: "#ff9b62" },
            { width: "60%", text: "Moyen", color: "#f3ca67" },
            { width: "80%", text: "Bon", color: "#78b4ff" },
            { width: "100%", text: "Excellent", color: "#70e3a4" }
        ];

        const level = password.length === 0
            ? levels[0]
            : levels[score];

        strengthBar.style.width = level.width;
        strengthBar.style.background = level.color;
        strengthText.textContent = level.text;

        checkPasswordMatch();
    });

    // Vérifier si les deux mots de passe correspondent
    function checkPasswordMatch() {
        const first = password1.value;
        const second = password2.value;

        if (!second) {
            passwordMessage.textContent = "";
            passwordMessage.className = "password-message";
            return false;
        }

        if (first === second) {
            passwordMessage.textContent = "Les mots de passe correspondent.";
            passwordMessage.className = "password-message success";
            return true;
        }

        passwordMessage.textContent = "Les mots de passe ne correspondent pas.";
        passwordMessage.className = "password-message error";
        return false;
    }

    password2.addEventListener("input", checkPasswordMatch);

    // Validation avant envoi
    form.addEventListener("submit", (event) => {
        formError.textContent = "";

        if (password1.value !== password2.value) {
            event.preventDefault();
            formError.textContent = "Les deux mots de passe ne correspondent pas.";
            password2.focus();
            return;
        }

        if (password1.value.length < 8) {
            event.preventDefault();
            formError.textContent = "Le mot de passe doit contenir au moins 8 caractères.";
            password1.focus();
        }
    });

});
