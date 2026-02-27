document.addEventListener('DOMContentLoaded', () => {
    // Finde alle Canvas-Elemente, die als Signature-Pad dienen sollen
    const signatureCanvases = document.querySelectorAll('.signature-pad');
    const signaturePads = {};

    signatureCanvases.forEach(canvas => {
        const fieldName = canvas.dataset.fieldName;
        const hiddenInput = document.getElementById(`signature64_${fieldName}`);
        const clearButton = document.getElementById(`clear_${fieldName}`);

        // Canvas an die tatsächliche Größe anpassen für scharfe Linien
        function resizeCanvas() {
            const ratio = Math.max(window.devicePixelRatio || 1, 1);
            canvas.width = canvas.offsetWidth * ratio;
            canvas.height = canvas.offsetHeight * ratio;
            canvas.getContext("2d").scale(ratio, ratio);
        }
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        // SignaturePad initialisieren
        const pad = new SignaturePad(canvas);
        signaturePads[fieldName] = pad;

        // Wenn wir vom "Bearbeiten" zurückkommen, Unterschrift wiederherstellen
        if (hiddenInput && hiddenInput.value) {
            pad.fromDataURL(hiddenInput.value);
        }

        // Löschen-Button Logik
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                pad.clear();
                if (hiddenInput) {
                    hiddenInput.value = '';
                }
            });
        }
    });

    // Formular-Submit Logik
    const form = document.getElementById('dynamicForm');
    if (form) {
        form.addEventListener('submit', (e) => {
            let isValid = true;

            // Alle Signature-Pads prüfen
            for (const [fieldName, pad] of Object.entries(signaturePads)) {
                const hiddenInput = document.getElementById(`signature64_${fieldName}`);
                const isRequired = hiddenInput && hiddenInput.hasAttribute('required');

                if (isRequired && pad.isEmpty() && !hiddenInput.value) {
                    isValid = false;
                    alert(`Bitte das Unterschriftsfeld "${fieldName}" ausfüllen!`);
                    break; // Schleife abbrechen beim ersten Fehler
                } else {
                    // Nur aktualisieren, wenn neu unterschrieben wurde
                    if (!pad.isEmpty() && hiddenInput) {
                        hiddenInput.value = pad.toDataURL();
                    }
                }
            }

            if (!isValid) {
                e.preventDefault(); // Absenden verhindern
            }
        });
    }
});