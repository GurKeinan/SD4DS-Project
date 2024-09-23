const predefinedImages = [
            'predefined-images/Gur.png',
            'predefined-images/Idan.png',
            'predefined-images/Noam.png',
            'predefined-images/Ori.png',
            'predefined-images/Stav.png',
            'predefined-images/Itamar.jpg',
        ];

        // Function to dynamically load predefined images
function loadPredefinedImages() {
            const imageContainer = document.getElementById('predefined_images');
            predefinedImages.forEach(imageSrc => {
                const imgElement = document.createElement('img');
                imgElement.src = `/static/${imageSrc}`;
                imgElement.alt = imageSrc.split('/').pop(); // Use the filename as alt text
                imgElement.class='img-fluid';
                // Set the onclick event to call selectPhoto with the image source
                imgElement.onclick = function() {
                    selectPhoto(`/static/${imageSrc}`);
                };

                imageContainer.appendChild(imgElement);
            });
        }

        // Load predefined images when the page is loaded

        window.onload = loadPredefinedImages;