        let imageFiles = [];
        let currentImageFile = null;

        // --- Simple Logger ---
        const logger = {
            _log(level, ...args) {
                const timestamp = new Date().toLocaleTimeString();
                console[level](`[${timestamp}]`, ...args);
            },
            log(...args) { this._log('log', ...args); },
            warn(...args) { this._log('warn', ...args); },
            error(...args) { this._log('error', ...args); }
        };
        logger.log("App initialized.");

        // --- Tab Loading Logic ---
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContentContainer = document.getElementById('tab-content');

        async function loadTabContent(tabName) {
            try {
                const response = await fetch(`src/tabs/${tabName}.html`);
                if (!response.ok) {
                    throw new Error(`Failed to load tab: ${tabName}`);
                }
                const content = await response.text();
                tabContentContainer.innerHTML = content;
                logger.log(`Successfully loaded tab: ${tabName}`);

                if (tabName === 'metadata' && imageFiles.length > 0) {
                    if (currentImageFile) {
                        displaySingleImage(currentImageFile, imageFiles.length > 1);
                    }
                }
            } catch (error) {
                logger.error(error);
                tabContentContainer.innerHTML = `<p class="text-red-500 text-center py-8">Error loading content. Please try again later.</p>`;
            }
        }

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                tabButtons.forEach(btn => btn.classList.remove('active-tab'));
                button.classList.add('active-tab');
                loadTabContent(tabName);
            });
        });

        // Load the initial active tab
        const initialTab = document.querySelector('.tab-button.active-tab');
        if (initialTab) {
            loadTabContent(initialTab.dataset.tab);
        }

        // DOM Element References
        const fileInput = document.getElementById('fileInput');
        const folderInput = document.getElementById('folderInput');
        const dropZone = document.getElementById('dropZone');
        const browseFilesButton = document.getElementById('browseFilesButton');
        const browseFolderButton = document.getElementById('browseFolderButton');
        const initialMessage = document.getElementById('initialMessage');
        const singleImagePreview = document.getElementById('singleImagePreview');
        const currentImage = document.getElementById('currentImage');
        const imageGallery = document.getElementById('imageGallery');
        const fileSelectorContainer = document.getElementById('fileSelectorContainer');
        const closePreviewButton = document.getElementById('closePreviewButton');
        const imageDisplay = document.getElementById('imageDisplay');
        const imageGalleryContainer = document.getElementById('imageGalleryContainer');

        // Modal DOM References
        const customModal = document.getElementById('customModal');
        const modalMessage = document.getElementById('modalMessage');
        const modalConfirmButton = document.getElementById('modalConfirmButton');
        const modalCancelButton = document.getElementById('modalCancelButton');

        // Lightbox DOM References
        const lightboxModal = document.getElementById('lightboxModal');
        const lightboxImage = document.getElementById('lightboxImage');
        const lightboxCloseButton = document.getElementById('lightboxCloseButton');

        // --- MODAL LOGIC ---
        let confirmCallback = null;
        let cancelCallback = null;

        function hideModal() {
            customModal.classList.add('hidden');
        }

        function showModal(message, onConfirm, onCancel) {
            modalMessage.textContent = message;
            confirmCallback = onConfirm;
            cancelCallback = onCancel;
            if (onCancel) {
                modalCancelButton.classList.remove('hidden');
            } else {
                modalCancelButton.classList.add('hidden');
            }
            modalConfirmButton.textContent = onCancel ? 'Confirm' : 'OK';
            customModal.classList.remove('hidden');
        }

        modalConfirmButton.addEventListener('click', () => {
            if (confirmCallback) confirmCallback();
            hideModal();
        });

        modalCancelButton.addEventListener('click', () => {
            if (cancelCallback) cancelCallback();
            hideModal();
        });

        function showAlert(message) {
            showModal(message, () => {}, null);
        }
        
        // Event Listeners
        browseFilesButton.addEventListener('click', () => fileInput.click());
        browseFolderButton.addEventListener('click', () => folderInput.click());
        fileInput.addEventListener('change', handleFiles);
        folderInput.addEventListener('change', handleFiles);
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
        closePreviewButton.addEventListener('click', confirmClosePreview);

        singleImagePreview.addEventListener('click', () => {
            if (currentImage.src) {
                lightboxImage.src = currentImage.src;
                lightboxModal.classList.remove('hidden');
            }
        });

        lightboxCloseButton.addEventListener('click', () => {
            lightboxModal.classList.add('hidden');
        });

        lightboxModal.addEventListener('click', (e) => {
            if (e.target === lightboxModal) {
                lightboxModal.classList.add('hidden');
            }
        });


        function clearContent(showSelector = true) {
            logger.log(`Clearing display. Show selector: ${showSelector}`);
            
            if (showSelector) {
                initialMessage.classList.remove('hidden');
            } else {
                initialMessage.classList.add('hidden');
            }

            singleImagePreview.classList.add('hidden');
            imageGalleryContainer.classList.add('hidden');
            imageGallery.innerHTML = '';
            const exifDataTable = document.getElementById('exifDataTable');
            if(exifDataTable) {
                const exifDataTableBody = exifDataTable.querySelector('tbody');
                exifDataTable.classList.add('hidden');
                exifDataTableBody.innerHTML = '';
            }
            imageDisplay.classList.remove('justify-center');

            if (showSelector) {
                fileSelectorContainer.classList.remove('hidden');
                closePreviewButton.classList.add('hidden');
            } else {
                fileSelectorContainer.classList.add('hidden');
                closePreviewButton.classList.remove('hidden');
            }
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function handleFiles(event) {
            logger.log(`Handling files from event: ${event.type}`);
            
            let files;
            if (event.type === 'change') {
                files = event.target.files;
            } else if (event.type === 'drop') {
                files = event.dataTransfer.files;
            }

            if (!files || files.length === 0) {
                logger.warn("File selection was cancelled or no files were chosen.");
                return;
            }
            
            clearContent(false);
            logger.log(`Found ${files.length} total files.`);

            imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
            logger.log(`Filtered to ${imageFiles.length} image files.`);

            if (imageFiles.length === 0) {
                showAlert('No valid image files found. Please select images or a folder containing them.');
                clearContent(true);
                return;
            }
            
            if (imageFiles.length === 1) {
                await displaySingleImage(imageFiles[0]);
            } else {
                await displayImageGallery(imageFiles);
                await displaySingleImage(imageFiles[0], true);
            }
        }

        async function displaySingleImage(file, inGalleryMode = false) {
            logger.log(`Displaying single image: ${file.name}`);
            currentImageFile = file;
            singleImagePreview.classList.remove('hidden');
            
            if (!inGalleryMode) {
                imageGalleryContainer.classList.add('hidden');
                imageDisplay.classList.add('justify-center');
            } else {
                imageDisplay.classList.remove('justify-center');
            }

            const exifInitialMessage = document.getElementById('exifInitialMessage');
            if(exifInitialMessage) {
                exifInitialMessage.classList.add('hidden');
            }
            const exifDataTable = document.getElementById('exifDataTable');
            if(exifDataTable) {
                exifDataTable.classList.remove('hidden');
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                currentImage.src = e.target.result;
                logger.log(`Image preview has been set for ${file.name}`);
            };
            reader.readAsDataURL(file);

            try {
                const exifTags = await exifr.parse(file);
                logger.log(`Successfully parsed EXIF data for ${file.name}`, exifTags || 'No EXIF data found.');
                const fileMetadata = {
                    'File Name': file.name,
                    'File Size': formatBytes(file.size),
                    'File Type': file.type,
                    'Last Modified': new Date(file.lastModified).toLocaleString()
                };
                populateExifTable(fileMetadata, exifTags || {});
            } catch (error) {
                logger.error(`Error parsing EXIF data for ${file.name}:`, error);
                const fileMetadata = {
                    'File Name': file.name,
                    'File Size': formatBytes(file.size),
                    'File Type': file.type,
                    'Last Modified': new Date(file.lastModified).toLocaleString()
                };
                populateExifTable(fileMetadata, { 'Error': 'Could not read EXIF data.' });
            }
        }

        async function displayImageGallery(files) {
            logger.log(`Displaying image gallery with ${files.length} images.`);
            imageFiles = files;
            imageGalleryContainer.classList.remove('hidden');
            
            imageGallery.innerHTML = '';
            imageFiles.forEach(file => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'relative group cursor-pointer rounded-md overflow-hidden shadow-sm hover:shadow-lg transition-all duration-200 ease-in-out aspect-square';
                    imgContainer.innerHTML = `
                        <img src="${e.target.result}" alt="${file.name}" class="w-full h-full object-cover">
                        <div class="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <p class="text-white text-xs font-semibold text-center p-2 truncate w-full">${file.name}</p>
                        </div>
                    `;
                    imgContainer.addEventListener('click', () => displaySingleImage(file, true));
                    imageGallery.appendChild(imgContainer);
                };
                reader.readAsDataURL(file);
            });
        }

        function populateExifTable(fileMetadata, exifTags) {
            logger.log("Populating metadata table.");
            const exifDataTable = document.getElementById('exifDataTable');
            if(exifDataTable) {
                const exifDataTableBody = exifDataTable.querySelector('tbody');
                exifDataTableBody.innerHTML = '';

                function addRow(tag, value) {
                    const row = exifDataTableBody.insertRow();
                    row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
                    const cellTag = row.insertCell();
                    const cellValue = row.insertCell();
                    cellTag.className = 'px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-200';
                    cellValue.className = 'px-6 py-4 text-sm text-gray-700 dark:text-gray-300 break-words max-w-xs';
                    cellTag.textContent = tag;
                    cellValue.textContent = value;
                }

                const fileMetaHeaderRow = exifDataTableBody.insertRow();
                fileMetaHeaderRow.innerHTML = `<td colspan="2" class="table-section-header rounded-t-md">File Metadata</td>`;
                for (const tag in fileMetadata) {
                    if (fileMetadata.hasOwnProperty(tag)) {
                        addRow(tag, fileMetadata[tag]);
                    }
                }

                const exifDataHeaderRow = exifDataTableBody.insertRow();
                exifDataHeaderRow.innerHTML = `<td colspan="2" class="table-section-header mt-4">EXIF Data</td>`;
                if (Object.keys(exifTags).length === 0) {
                    addRow('N/A', 'No EXIF data found for this image.');
                } else {
                    for (const tag in exifTags) {
                        if (exifTags.hasOwnProperty(tag)) {
                            const value = Array.isArray(exifTags[tag]) ? exifTags[tag].join(', ') : exifTags[tag];
                            addRow(tag, value);
                        }
                    }
                }
            }
        }

        function handleDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over');
        }

        function handleDragLeave(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
        }

        function handleDrop(e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
            handleFiles(e);
        }

        function confirmClosePreview() {
            showModal(
                'Are you sure you want to close the current preview and return to file selection?',
                () => { 
                    clearContent(true); 
                    // Reset inputs to allow re-selecting the same file
                    fileInput.value = null;
                    folderInput.value = null;
                    logger.log("Preview closed and file inputs reset.");
                },
                () => {}
            );
        }

        clearContent(true);
        // Initial reset of inputs on page load
        fileInput.value = null;
        folderInput.value = null;

        // Theme Toggle Script
        const themeToggle = document.getElementById('theme-toggle');
        const themeIconLight = document.getElementById('theme-icon-light');
        const themeIconDark = document.getElementById('theme-icon-dark');

        if (localStorage.getItem('theme') === 'dark' || (!('theme in localStorage') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            themeIconLight.classList.add('hidden');
            themeIconDark.classList.remove('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            themeIconLight.classList.remove('hidden');
            themeIconDark.classList.add('hidden');
        }

        themeToggle.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            if (document.documentElement.classList.contains('dark')) {
                localStorage.setItem('theme', 'dark');
                themeIconLight.classList.add('hidden');
                themeIconDark.classList.remove('hidden');
            } else {
                localStorage.setItem('theme', 'light');
                themeIconLight.classList.remove('hidden');
                themeIconDark.classList.add('hidden');
            }
        });