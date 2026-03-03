import * as pdfjsLib from 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.min.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs';

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('pdf-canvas');
    if (!canvas) return;

    const pdfUrl = canvas.dataset.pdfUrl;
    const ctx = canvas.getContext('2d');
    const loading = document.getElementById('pdf-loading');
    const nav = document.getElementById('pdf-nav');
    const prevBtn = document.getElementById('pdf-prev');
    const nextBtn = document.getElementById('pdf-next');
    const pageInfo = document.getElementById('pdf-page-info');

    const DEFAULT_CONTAINER_WIDTH = 760;
    let pdfDoc = null;
    let currentPage = 1;
    let rendering = false;

    function renderPage(pageNum) {
        if (rendering) return;
        rendering = true;

        pdfDoc.getPage(pageNum).then(page => {
            const devicePixelRatio = window.devicePixelRatio || 1;
            const containerWidth = canvas.parentElement.clientWidth || DEFAULT_CONTAINER_WIDTH;
            const scale = containerWidth / page.getViewport({ scale: 1 }).width;
            const viewport = page.getViewport({ scale: scale * devicePixelRatio });

            canvas.width = viewport.width;
            canvas.height = viewport.height;
            canvas.style.width = `${viewport.width / devicePixelRatio}px`;
            canvas.style.height = `${viewport.height / devicePixelRatio}px`;

            return page.render({ canvasContext: ctx, viewport }).promise;
        }).then(() => {
            rendering = false;
            pageInfo.textContent = `Seite ${currentPage} von ${pdfDoc.numPages}`;
            prevBtn.disabled = currentPage <= 1;
            nextBtn.disabled = currentPage >= pdfDoc.numPages;
        }).catch(err => {
            rendering = false;
            console.error('Fehler beim Rendern der Seite:', err);
        });
    }

    pdfjsLib.getDocument(pdfUrl).promise.then(doc => {
        pdfDoc = doc;
        if (loading) loading.style.display = 'none';
        canvas.style.display = 'block';
        if (nav) nav.style.display = 'flex';
        renderPage(currentPage);
    }).catch(err => {
        if (loading) loading.textContent = 'Fehler beim Laden des PDFs.';
        console.error('Fehler beim Laden des PDFs:', err);
    });

    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderPage(currentPage);
        }
    });

    nextBtn.addEventListener('click', () => {
        if (pdfDoc && currentPage < pdfDoc.numPages) {
            currentPage++;
            renderPage(currentPage);
        }
    });
});
