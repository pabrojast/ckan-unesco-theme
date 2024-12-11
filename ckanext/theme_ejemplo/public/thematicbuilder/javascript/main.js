let catalogData = null;
let selectionMap = {};

document.addEventListener('DOMContentLoaded', function() {
    const fileSelect = document.getElementById('thematicbuilder-file-select');
    const fileInput = document.getElementById('thematicbuilder-file-input');
    const searchInput = document.getElementById('thematicbuilder-search-input');
    const includeTagsCheckbox = document.getElementById('include-tags');
    
    let jsonFiles = []; // Archivos JSON disponibles
    
    // Carga la lista de archivos JSON disponibles
    fetch('https://ihp-wins.unesco.org/api/3/action/package_show?id=terriajs-map-catalog-in-json-format')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.result.resources) {
                // Filtra sólo archivos JSON y ordena por nombre
                jsonFiles = data.result.resources
                    .filter(resource => resource.format === 'JSON')
                    .sort((a, b) => a.name.localeCompare(b.name));
                
                updateFileList(jsonFiles, includeTagsCheckbox.checked);
            }
        })
        .catch(error => console.error('Error loading files:', error));
    
    // Cambios en el checkbox de tags
    includeTagsCheckbox.addEventListener('change', function() {
        updateFileList(jsonFiles, this.checked);
    });
    
    function updateFileList(files, includeTags) {
        // Limpia opciones del select (excepto la primera)
        while (fileSelect.options.length > 1) {
            fileSelect.remove(1);
        }
        
        files.filter(file => {
            const isTagFile = file.name.toLowerCase().startsWith('tag_');
            return includeTags || !isTagFile;
        }).forEach(file => {
            const option = document.createElement('option');
            option.value = file.url;
            option.textContent = file.name;
            fileSelect.appendChild(option);
        });
    }
    
    // Manejo de carga manual de archivos
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    processJsonFile(data);
                    fileSelect.value = ''; // Limpia la selección en el select
                } catch (error) {
                    console.error('Error parsing JSON file:', error);
                }
            };
            reader.readAsText(file);
        }
    });
    
    // Manejo de la selección de archivo desde el dropdown
    fileSelect.addEventListener('change', function() {
        if (this.value) {
            fileInput.value = ''; // Limpia input de archivos
            fetch(this.value)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    processJsonFile(data);
                })
                .catch(error => {
                    console.error('Error loading file:', error);
                    alert('Error loading the selected file. Please try again or choose another file.');
                });
        }
    });

    // Búsqueda
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            renderCatalogItems(catalogData.catalog);
        });
    }
});

function processJsonFile(data) {
    catalogData = data;
    selectionMap = {}; // Reinicia el mapa de selección
    
    const itemList = document.getElementById('thematicbuilder-item-list');
    itemList.innerHTML = '';
    
    // Mostrar items del catálogo
    if (data.catalog) {
        renderCatalogItems(data.catalog);
        document.getElementById('thematicbuilder-download-btn').style.display = 'block';
        updateSelectedCount();
    } else {
        console.error('Invalid catalog format');
    }
}

function renderCatalogItems(items, parentIndex = "") {
    const itemList = document.getElementById('thematicbuilder-item-list');
    itemList.innerHTML = ''; // Limpia items existentes
    
    const searchTerm = document.getElementById('thematicbuilder-search-input')?.value.toLowerCase() || '';
    
    function processGroup(groupItems, parentIdx = "", level = 0) {
        groupItems.forEach((item, index) => {
            const currentIndex = parentIdx ? `${parentIdx}-${index}` : `${index}`;
            const matchesSearch = item.name && item.name.toLowerCase().includes(searchTerm);
            const hasVisibleChildren = item.members && hasChildrenMatching(item.members, searchTerm);
            const shouldDisplay = matchesSearch || hasVisibleChildren || level === 0;

            if (shouldDisplay) {
                const li = document.createElement('li');
                li.className = 'thematicbuilder-item';

                const hasSubgroups = item.members && item.members.length > 0;
                if (hasSubgroups) {
                    li.classList.add('thematicbuilder-group');
                }

                if (level > 0) {
                    li.classList.add('thematicbuilder-item-indent');
                }

                const checkboxHTML = `
                    <div class="thematicbuilder-checkbox-container">
                        <input type="checkbox" data-index="${currentIndex}" ${isItemSelected(currentIndex) ? 'checked' : ''}>
                    </div>
                `;

                if (level === 0 && index === 0) {
                    li.innerHTML = `
                        ${checkboxHTML}
                        <div class="thematicbuilder-item-content">
                            <span class="thematicbuilder-level-indicator">Root</span>
                            <span class="thematicbuilder-group-name">${item.name}</span>
                            <span class="thematicbuilder-meta">(Main element)</span>
                        </div>
                    `;
                } else {
                    li.innerHTML = `
                        ${checkboxHTML}
                        <div class="thematicbuilder-item-content">
                            ${hasSubgroups ? '<span class="thematicbuilder-group-icon">📁</span>' : '<span class="thematicbuilder-group-icon">📄</span>'}
                            <span class="${hasSubgroups ? 'thematicbuilder-group-name' : 'thematicbuilder-item-name'}">${item.name}</span>
                            ${hasSubgroups ? `<span class="thematicbuilder-meta">(${item.members.length} items)</span>` : ''}
                        </div>
                    `;
                }
                itemList.appendChild(li);
            }

            if (item.members && Array.isArray(item.members)) {
                processGroup(item.members, currentIndex, level + 1);
            }
        });
    }

    if (items && Array.isArray(items)) {
        processGroup(items);
    }
}

function hasChildrenMatching(items, term) {
    for (const item of items) {
        const matches = item.name && item.name.toLowerCase().includes(term);
        const hasSubMatches = item.members && hasChildrenMatching(item.members, term);
        if (matches || hasSubMatches) {
            return true;
        }
    }
    return false;
}

function isItemSelected(indexPath) {
    if (selectionMap[indexPath] === undefined) {
        return true;
    }
    return !!selectionMap[indexPath];
}

function updateSelectedCount() {
    const selectedCount = Object.values(selectionMap).filter(Boolean).length;
    const countElement = document.getElementById('thematicbuilder-selected-count');
    if (countElement) {
        countElement.textContent = `Selected items: ${selectedCount}`;
    }
}

// Manejo del check de items
document.getElementById('thematicbuilder-item-list').addEventListener('change', function(e) {
    if (e.target.type === 'checkbox') {
        const idx = e.target.dataset.index;
        selectionMap[idx] = e.target.checked;
        toggleGroupChildren(idx, e.target.checked);
        updateSelectedCount();
    }
});

function toggleGroupChildren(parentIndex, checked) {
    const itemList = document.getElementById('thematicbuilder-item-list');
    const checkboxes = itemList.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(chk => {
        const idx = chk.dataset.index;
        if (idx !== parentIndex && idx.startsWith(parentIndex)) {
            chk.checked = checked;
            selectionMap[idx] = checked;
        }
    });
}

// Evento para descargar el JSON filtrado
document.getElementById('thematicbuilder-download-btn').addEventListener('click', function() {
    if (!catalogData) return;

    const filteredCatalog = {
        catalog: filterData(catalogData.catalog, "")
    };

    // Ahora generamos workbench, focusWorkbenchItems y models basados en elementos seleccionados
    const { models, workbench } = createModelsAndWorkbench(filteredCatalog.catalog);

    filteredCatalog.workbench = workbench;
    filteredCatalog.focusWorkbenchItems = true;
    filteredCatalog.models = models;

    const jsonString = JSON.stringify(filteredCatalog, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'modified_catalog.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

function filterData(items, parentIndex) {
    const result = [];
    items.forEach((item, index) => {
        const currentIndex = parentIndex ? `${parentIndex}-${index}` : `${index}`;
        const selected = isItemSelected(currentIndex);
        const hasMembers = item.members && Array.isArray(item.members) && item.members.length > 0;

        if (selected) {
            const newItem = { ...item };
            if (hasMembers) {
                newItem.members = filterData(item.members, currentIndex);
            }
            result.push(newItem);
        } else if (hasMembers) {
            const filteredMembers = filterData(item.members, currentIndex);
            if (filteredMembers.length > 0) {
                const newItem = { ...item, members: filteredMembers };
                result.push(newItem);
            }
        }
    });
    return result;
}

// Crea el diccionario models y la lista workbench a partir del catálogo filtrado
function createModelsAndWorkbench(catalogItems) {
    const models = {};
    const workbench = [];

    // Modelo raíz
    models["/"] = {
        "type": "group"
    };

    // Función recursiva para crear modelos
    function processItems(items, parentModelId = "/") {
        items.forEach(item => {
            if (item.type && item.type === "group") {
                // Es un grupo
                const groupModelId = "///" + item.name;
                models[groupModelId] = {
                    "isOpen": true,
                    "knownContainerUniqueIds": [ parentModelId ],
                    "type": "group"
                };
                if (item.members && item.members.length > 0) {
                    processItems(item.members, groupModelId);
                }
            } else {
                // Es un ítem (csv, shp, etc.)
                // Debe tener un id
                if (item.id) {
                    models[item.id] = {
                        "show": true,
                        "isOpenInWorkbench": true,
                        "knownContainerUniqueIds": [ parentModelId ],
                        "type": item.type || "csv"
                    };
                    // Lo agregamos al workbench
                    workbench.push(item.id);
                }
            }
        });
    }

    processItems(catalogItems, "/");
    return { models, workbench };
}
