// Asocia eventos a los elementos del DOM para manejar las interacciones del usuario.
document.getElementById('imageInput').addEventListener('change', handleImageUpload);
document.getElementById('thresholdInput').addEventListener('input', updateThreshold);
document.getElementById('compressButton').addEventListener('click', compressImage);
document.getElementById('decompressButton').addEventListener('click', decompressImage);
document.getElementById('saveButton').addEventListener('click', saveCompressedImage);

let originalImageData; // Variable global para almacenar los datos de la imagen original.
let compressedImageData; // Variable global para almacenar los datos de la imagen comprimida.

// Función que maneja la carga de la imagen.
function handleImageUpload(event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    // Cuando el archivo se carga, se convierte en una imagen.
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.getElementById('originalCanvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            originalImageData = ctx.getImageData(0, 0, img.width, img.height);
        }
        img.src = e.target.result;
    }
    reader.readAsDataURL(file); // Lee el archivo como una URL de datos.
}

// Función que actualiza el valor del umbral en la interfaz de usuario.
function updateThreshold(event) {
    document.getElementById('thresholdValue').textContent = event.target.value;
}

// Función que comprime la imagen usando el algoritmo de quadtree.
function compressImage() {
    if (!originalImageData) {
        console.error('No se ha cargado ninguna imagen original.');
        return;
    }

    const threshold = document.getElementById('thresholdInput').value;
    compressedImageData = compressUsingQuadTree(originalImageData, 0, 0, originalImageData.width, originalImageData.height, threshold);

    const canvas = document.getElementById('compressedCanvas');
    canvas.width = compressedImageData.width;
    canvas.height = compressedImageData.height;
    const ctx = canvas.getContext('2d');
    ctx.putImageData(compressedImageData, 0, 0);
}

// Función que descomprime la imagen (aquí simplemente vuelve a mostrar la original).
function decompressImage() {
    if (!compressedImageData) {
        console.error('No se ha comprimido ninguna imagen aún.');
        return;
    }

    const canvas = document.getElementById('decompressedCanvas');
    canvas.width = originalImageData.width;
    canvas.height = originalImageData.height;
    const ctx = canvas.getContext('2d');
    ctx.putImageData(originalImageData, 0, 0);
}

// Función que guarda la imagen comprimida en un archivo.
function saveCompressedImage() {
    if (!compressedImageData) {
        console.error('No hay imagen comprimida para guardar.');
        return;
    }

    const link = document.createElement('a');
    link.download = 'compressed_image.png';

    const canvas = document.createElement('canvas');
    canvas.width = compressedImageData.width;
    canvas.height = compressedImageData.height;
    const ctx = canvas.getContext('2d');
    ctx.putImageData(compressedImageData, 0, 0);

    // Convierte el contenido del canvas a un blob y crea un enlace para descargarlo.
    canvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
    }, 'image/png');
}

// Función que comprime una imagen usando el algoritmo de quadtree.
function compressUsingQuadTree(imageData, x, y, width, height, threshold) {
    if (width <= 0 || height <= 0) {
        return createImageData(imageData.width, imageData.height);
    }

    // Calcula el color promedio de una región de la imagen.
    function calculateAverageColor(imageData, x, y, width, height) {
        let totalR = 0, totalG = 0, totalB = 0, count = 0;

        for (let i = x; i < x + width; i++) {
            for (let j = y; j < y + height; j++) {
                const index = (j * imageData.width + i) * 4;
                totalR += imageData.data[index];
                totalG += imageData.data[index + 1];
                totalB += imageData.data[index + 2];
                count++;
            }
        }

        return {
            r: totalR / count,
            g: totalG / count,
            b: totalB / count
        };
    }

    // Calcula la varianza de color en una región de la imagen.
    function calculateColorVariance(imageData, x, y, width, height, averageColor) {
        let variance = 0;

        for (let i = x; i < x + width; i++) {
            for (let j = y; j < y + height; j++) {
                const index = (j * imageData.width + i) * 4;
                const r = imageData.data[index];
                const g = imageData.data[index + 1];
                const b = imageData.data[index + 2];
                variance += (r - averageColor.r) ** 2 + (g - averageColor.g) ** 2 + (b - averageColor.b) ** 2;
            }
        }

        return variance / (width * height);
    }

    // Crea un objeto ImageData vacío con el tamaño especificado.
    function createImageData(width, height) {
        return new ImageData(width, height);
    }

    const averageColor = calculateAverageColor(imageData, x, y, width, height);
    const variance = calculateColorVariance(imageData, x, y, width, height, averageColor);

    // Si la varianza es menor que el umbral, llena la región con el color promedio.
    if (variance < threshold) {
        const compressedImageData = createImageData(width, height);

        for (let i = 0; i < width; i++) {
            for (let j = 0; j < height; j++) {
                const index = (j * width + i) * 4;
                compressedImageData.data[index] = averageColor.r;
                compressedImageData.data[index + 1] = averageColor.g;
                compressedImageData.data[index + 2] = averageColor.b;
                compressedImageData.data[index + 3] = 255; // Full opacity
            }
        }

        return compressedImageData;
    } else {
        // Si la varianza es mayor que el umbral, divide la región y comprime cada subregión.
        const halfWidth = Math.floor(width / 2);
        const halfHeight = Math.floor(height / 2);

        const topLeft = compressUsingQuadTree(imageData, x, y, halfWidth, halfHeight, threshold);
        const topRight = compressUsingQuadTree(imageData, x + halfWidth, y, width - halfWidth, halfHeight, threshold);
        const bottomLeft = compressUsingQuadTree(imageData, x, y + halfHeight, halfWidth, height - halfHeight, threshold);
        const bottomRight = compressUsingQuadTree(imageData, x + halfWidth, y + halfHeight, width - halfWidth, height - halfHeight, threshold);

        const combinedImageData = createImageData(width, height);
        const contexts = [topLeft, topRight, bottomLeft, bottomRight];
        const offsets = [
            { x: 0, y: 0 },
            { x: halfWidth, y: 0 },
            { x: 0, y: halfHeight },
            { x: halfWidth, y: halfHeight }
        ];

        // Combina las subregiones comprimidas en una sola imagen.
        for (let k = 0; k < 4; k++) {
            const context = contexts[k];
            const offset = offsets[k];
            for (let i = 0; i < context.width; i++) {
                for (let j = 0; j < context.height; j++) {
                    const srcIndex = (j * context.width + i) * 4;
                    const destIndex = ((j + offset.y) * width + (i + offset.x)) * 4;
                    combinedImageData.data[destIndex] = context.data[srcIndex];
                    combinedImageData.data[destIndex + 1] = context.data[srcIndex + 1];
                    combinedImageData.data[destIndex + 2] = context.data[srcIndex + 2];
                    combinedImageData.data[destIndex + 3] = context.data[srcIndex + 3];
                }
            }
        }

        return combinedImageData;
    }
}
