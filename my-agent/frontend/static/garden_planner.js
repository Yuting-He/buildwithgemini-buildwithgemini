/**
 * FloraGuide Visual Garden Planner Engine
 * Digital Twin interactive garden workspace supporting:
 * - 2D editing canvas (freehand, smoothed polygon, rectangle, vertex editing)
 * - 3D isometric WebGL scene with procedural botanical models, pots, raised beds, lighting, shadows
 * - Collapsible plant library (existing plants placed vs awaiting placement, botanical presets)
 * - Plant condition halos & prioritized status monitoring
 * - Interactive plant side panel with quick care actions (watering, observations, photos)
 * - Auto-save & layout persistence
 */

(function (window) {
  'use strict';

  // --- Plant Presets Catalog ---
  const PLANT_PRESETS = [
    {
      id_prefix: 'preset-basil',
      name: 'Sweet Basil',
      species: 'Ocimum basilicum',
      plant_type: 'herb',
      planting_type: 'container',
      container_size_liters: 4.0,
      substrate_type: 'potting mix',
      drainage_quality: 'good',
      icon: '🌿',
      description: 'Aromatic culinary herb, loves warm sun and well-draining soil.'
    },
    {
      id_prefix: 'preset-mint',
      name: 'Spearmint',
      species: 'Mentha spicata',
      plant_type: 'herb',
      planting_type: 'container',
      container_size_liters: 5.0,
      substrate_type: 'rich potting soil',
      drainage_quality: 'good',
      icon: '🌱',
      description: 'Vigorous herb; best kept in containers to prevent invasive root spreading.'
    },
    {
      id_prefix: 'preset-rosemary',
      name: 'Tuscan Rosemary',
      species: 'Salvia rosmarinus',
      plant_type: 'herb',
      planting_type: 'container',
      container_size_liters: 7.5,
      substrate_type: 'sandy loam',
      drainage_quality: 'excellent',
      icon: '🪴',
      description: 'Woody perennial herb with needle foliage, drought-tolerant.'
    },
    {
      id_prefix: 'preset-lavender',
      name: 'English Lavender',
      species: 'Lavandula angustifolia',
      plant_type: 'flower',
      planting_type: 'container',
      container_size_liters: 6.0,
      substrate_type: 'lean rocky soil',
      drainage_quality: 'excellent',
      icon: '🪻',
      description: 'Fragrant purple flower spikes, thrives in bright sun and low moisture.'
    },
    {
      id_prefix: 'preset-marigold',
      name: 'French Marigold',
      species: 'Tagetes patula',
      plant_type: 'flower',
      planting_type: 'ground',
      container_size_liters: null,
      substrate_type: 'garden loam',
      drainage_quality: 'good',
      icon: '🌼',
      description: 'Golden pest-deterrent companion flower, blooms all season.'
    },
    {
      id_prefix: 'preset-hydrangea',
      name: 'Blue Hydrangea',
      species: 'Hydrangea macrophylla',
      plant_type: 'shrub',
      planting_type: 'ground',
      container_size_liters: null,
      substrate_type: 'acidic moist soil',
      drainage_quality: 'good',
      icon: '🌸',
      description: 'Lush flowering shrub with rich globose blossoms, prefers morning sun.'
    },
    {
      id_prefix: 'preset-blueberry',
      name: 'Highbush Blueberry',
      species: 'Vaccinium corymbosum',
      plant_type: 'shrub',
      planting_type: 'container',
      container_size_liters: 25.0,
      substrate_type: 'acidic peat & bark',
      drainage_quality: 'good',
      icon: '🫐',
      description: 'Deciduous berry shrub with sweet fruit and vibrant autumn foliage.'
    },
    {
      id_prefix: 'preset-boxwood',
      name: 'English Boxwood',
      species: 'Buxus sempervirens',
      plant_type: 'shrub',
      planting_type: 'ground',
      container_size_liters: null,
      substrate_type: 'well-drained loam',
      drainage_quality: 'good',
      icon: '🌳',
      description: 'Dense evergreen shrub suitable for borders, hedges, and architectural accents.'
    },
    {
      id_prefix: 'preset-tomato',
      name: 'Cherry Tomato',
      species: 'Solanum lycopersicum var. cerasiforme',
      plant_type: 'vegetable',
      planting_type: 'container',
      container_size_liters: 15.0,
      substrate_type: 'rich composted soil',
      drainage_quality: 'good',
      icon: '🍅',
      description: 'Prolific producer of sweet bite-sized tomatoes, requires sun and regular support.'
    },
    {
      id_prefix: 'preset-pepper',
      name: 'Sweet Bell Pepper',
      species: 'Capsicum annuum',
      plant_type: 'vegetable',
      planting_type: 'container',
      container_size_liters: 10.0,
      substrate_type: 'organic potting mix',
      drainage_quality: 'good',
      icon: '🫑',
      description: 'Crisp bell peppers requiring warm conditions and consistent moisture.'
    },
    {
      id_prefix: 'preset-lettuce',
      name: 'Butterhead Lettuce',
      species: 'Lactuca sativa',
      plant_type: 'vegetable',
      planting_type: 'ground',
      container_size_liters: null,
      substrate_type: 'humus-rich soil',
      drainage_quality: 'good',
      icon: '🥬',
      description: 'Tender sweet salad greens, excels in cool seasons and partial shade.'
    },
    {
      id_prefix: 'preset-olive',
      name: 'Dwarf Olive Tree',
      species: 'Olea europaea "Arbequina"',
      plant_type: 'tree',
      planting_type: 'container',
      container_size_liters: 45.0,
      substrate_type: 'mediterranean gravel blend',
      drainage_quality: 'excellent',
      icon: '🫒',
      description: 'Silvery evergreen foliage, compact habit suited for patio containers.'
    },
    {
      id_prefix: 'preset-lemon',
      name: 'Meyer Lemon Tree',
      species: 'Citrus x meyeri',
      plant_type: 'tree',
      planting_type: 'container',
      container_size_liters: 40.0,
      substrate_type: 'citrus & cactus mix',
      drainage_quality: 'excellent',
      icon: '🍋',
      description: 'Sweet scented blooms and juicy aromatic lemons, needs warmth and bright light.'
    }
  ];

  // --- Geometry & Math Helpers ---
  const Geometry = {
    distance(p1, p2) {
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      return Math.sqrt(dx * dx + dy * dy);
    },

    pointInPolygon(point, polygon) {
      if (!polygon || polygon.length < 3) return false;
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].x, yi = polygon[i].y;
        const xj = polygon[j].x, yj = polygon[j].y;
        const intersect = ((yi > point.y) !== (yj > point.y)) &&
          (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
      }
      return inside;
    },

    polygonCentroid(polygon) {
      if (!polygon || polygon.length === 0) return { x: 0, y: 0 };
      let cx = 0, cy = 0;
      for (let p of polygon) {
        cx += p.x;
        cy += p.y;
      }
      return { x: cx / polygon.length, y: cy / polygon.length };
    },

    polygonBounds(polygon) {
      if (!polygon || polygon.length === 0) return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (let p of polygon) {
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
      }
      return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
    },

    // Douglas-Peucker point reduction for smoothing freehand inputs
    douglasPeucker(points, tolerance) {
      if (points.length <= 2) return points;
      let dmax = 0;
      let index = 0;
      const end = points.length - 1;

      for (let i = 1; i < end; i++) {
        const d = this.perpendicularDistance(points[i], points[0], points[end]);
        if (d > dmax) {
          index = i;
          dmax = d;
        }
      }

      if (dmax > tolerance) {
        const recResults1 = this.douglasPeucker(points.slice(0, index + 1), tolerance);
        const recResults2 = this.douglasPeucker(points.slice(index), tolerance);
        return recResults1.slice(0, recResults1.length - 1).concat(recResults2);
      } else {
        return [points[0], points[end]];
      }
    },

    perpendicularDistance(p, lineStart, lineEnd) {
      let dx = lineEnd.x - lineStart.x;
      let dy = lineEnd.y - lineStart.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return this.distance(p, lineStart);
      return Math.abs(dy * p.x - dx * p.y + lineEnd.x * lineStart.y - lineEnd.y * lineStart.x) / len;
    },

    // Chaikin smoothing algorithm to round polygonal edges into organic curves
    chaikinSmooth(points, iterations = 2) {
      if (points.length < 3) return points;
      let current = points.slice();

      for (let iter = 0; iter < iterations; iter++) {
        const next = [];
        const n = current.length;
        for (let i = 0; i < n; i++) {
          const p0 = current[i];
          const p1 = current[(i + 1) % n];
          next.push({
            x: 0.75 * p0.x + 0.25 * p1.x,
            y: 0.75 * p0.y + 0.25 * p1.y
          });
          next.push({
            x: 0.25 * p0.x + 0.75 * p1.x,
            y: 0.25 * p0.y + 0.75 * p1.y
          });
        }
        current = next;
      }
      return current;
    }
  };

  // --- Main GardenPlanner Controller ---
  class GardenPlanner {
    constructor() {
      this.garden = null;
      this.growingAreas = [];
      this.plants = [];
      this.layout = { areas: [], plants: [] };

      // UI States
      this.currentViewMode = 'visual'; // 'visual' | 'list'
      this.activeDimension = '2d';     // '2d' | '3d'
      this.activeMode = 'edit';        // 'explore' | 'edit'
      this.activeTool = 'select';      // 'select' | 'freehand' | 'rect' | 'polygon'

      this.selectedPlantId = null;
      this.selectedAreaId = null;
      this.filterCondition = 'all';
      this.filterAreaId = 'all';

      // 2D Canvas State
      this.canvas = null;
      this.ctx = null;
      this.panX = 50;
      this.panY = 50;
      this.zoom = 1.0;
      this.isPanning = false;
      this.panStart = { x: 0, y: 0 };

      // Freehand & Drawing State
      this.isDrawing = false;
      this.freehandPoints = [];
      this.polygonPoints = [];
      this.rectStart = null;
      this.rectCurrent = null;

      // Transform / Drag state
      this.isDraggingObject = false;
      this.dragTargetType = null; // 'plant' | 'area' | 'vertex'
      this.dragStartWorld = { x: 0, y: 0 };
      this.dragVertexIndex = -1;
      this.ghostPlant = null; // for drag from library

      // 3D Three.js State
      this.threeContainer = null;
      this.threeRenderer = null;
      this.threeScene = null;
      this.threeCamera = null;
      this.threeControls = null;
      this.threeRaycaster = null;
      this.threeMouse = null;
      this.threePlantMeshes = {}; // plantId -> mesh
      this.threeAreaMeshes = {};  // areaId -> mesh

      // History for Undo/Redo
      this.undoStack = [];
      this.redoStack = [];

      this.saveDebounceTimer = null;
      this.touchPendingPlant = null; // for tap-to-place on mobile
    }

    init() {
      this.bindElements();
      this.setupCanvas2D();
      this.setupThree3D();
      this.bindEvents();
    }

    bindElements() {
      this.canvas = document.getElementById('garden-canvas-2d');
      if (this.canvas) {
        this.ctx = this.canvas.getContext('2d');
      }
      this.threeContainer = document.getElementById('garden-canvas-3d-container');
    }

    // --- Loading & Synchronization ---
    async loadGardenData() {
      try {
        const summary = await fetchJSON('/api/garden');
        if (!summary) return;

        this.garden = summary.garden;
        this.growingAreas = summary.growing_areas || [];
        this.plants = summary.plants || [];

        // Load persisted layout
        const layoutRes = await fetchJSON('/api/garden/layout');
        if (layoutRes && layoutRes.layout && layoutRes.layout.areas && layoutRes.layout.areas.length > 0) {
          this.layout = layoutRes.layout;
          this.reconcileLayoutWithDatabase();
        } else {
          // Generate an initial sensible layout if no layout exists yet
          this.generateInitialLayout();
          this.scheduleSave();
        }

        this.renderAll();
      } catch (e) {
        console.error("Error loading garden planner data:", e);
      }
    }

    reconcileLayoutWithDatabase() {
      // Ensure all SQLite areas have layout entries
      const areaMap = new Map();
      this.layout.areas.forEach(a => areaMap.set(a.id, a));

      this.growingAreas.forEach((dbArea, idx) => {
        if (!areaMap.has(dbArea.id)) {
          // Create layout shape for unmapped area
          const startX = 80 + (idx % 3) * 360;
          const startY = 80 + Math.floor(idx / 3) * 300;
          const defaultShape = [
            { x: startX, y: startY },
            { x: startX + 300, y: startY },
            { x: startX + 300, y: startY + 220 },
            { x: startX, y: startY + 220 }
          ];
          this.layout.areas.push({
            id: dbArea.id,
            name: dbArea.name,
            area_type: dbArea.area_type || 'balcony',
            shape_type: 'rectangle',
            points: defaultShape,
            rotation: 0
          });
        } else {
          // Sync name and type
          const la = areaMap.get(dbArea.id);
          la.name = dbArea.name;
          la.area_type = dbArea.area_type;
        }
      });

      // Remove layout areas that were deleted in SQLite
      const validAreaIds = new Set(this.growingAreas.map(a => a.id));
      this.layout.areas = this.layout.areas.filter(a => validAreaIds.has(a.id));

      // Reconcile plants
      const plantMap = new Map();
      this.layout.plants.forEach(p => plantMap.set(p.id, p));

      // Remove layout plants that don't exist in SQLite
      const validPlantIds = new Set(this.plants.map(p => p.id));
      this.layout.plants = this.layout.plants.filter(p => validPlantIds.has(p.id));

      // Infer plant_type from name or species if missing
      this.layout.plants.forEach(p => {
        const dbPlant = this.plants.find(dp => dp.id === p.id);
        if (dbPlant) {
          p.name = dbPlant.name;
          p.area_id = dbPlant.area_id;
          p.planting_type = dbPlant.planting_type || 'container';
          if (!p.plant_type) p.plant_type = this.inferPlantType(dbPlant.name, dbPlant.species);
        }
      });
    }

    generateInitialLayout() {
      this.layout = { areas: [], plants: [] };

      // Generate a pleasant starting garden layout
      if (this.growingAreas.length === 0) {
        this.growingAreas.push({
          id: 'area-balcony',
          name: 'Main Balcony',
          area_type: 'balcony',
          sun_exposure: 'partial sun',
          shelter_from_rain: true,
          watering_arrangements: 'Manual watering can'
        });
      }

      this.growingAreas.forEach((area, i) => {
        const startX = 80 + i * 380;
        const startY = 100;
        const points = [
          { x: startX, y: startY },
          { x: startX + 320, y: startY },
          { x: startX + 320, y: startY + 240 },
          { x: startX, y: startY + 240 }
        ];
        this.layout.areas.push({
          id: area.id,
          name: area.name,
          area_type: area.area_type || 'balcony',
          shape_type: 'rectangle',
          points: points,
          rotation: 0
        });
      });

      // Distribute existing plants into their corresponding areas
      this.growingAreas.forEach((area) => {
        const areaLayout = this.layout.areas.find(a => a.id === area.id);
        if (!areaLayout) return;

        const bounds = Geometry.polygonBounds(areaLayout.points);
        const areaPlants = this.plants.filter(p => p.area_id === area.id);

        areaPlants.forEach((p, idx) => {
          const col = idx % 3;
          const row = Math.floor(idx / 3);
          const px = bounds.minX + 60 + col * 100;
          const py = bounds.minY + 60 + row * 90;

          this.layout.plants.push({
            id: p.id,
            area_id: p.area_id,
            name: p.name,
            plant_type: this.inferPlantType(p.name, p.species),
            x: px,
            y: py,
            scale: 1.0,
            rotation: 0,
            planting_type: p.planting_type || 'container'
          });
        });
      });
    }

    inferPlantType(name = '', species = '') {
      const text = (name + ' ' + species).toLowerCase();
      if (text.includes('tree') || text.includes('olive') || text.includes('lemon') || text.includes('fig') || text.includes('citrus')) return 'tree';
      if (text.includes('tomato') || text.includes('pepper') || text.includes('lettuce') || text.includes('zucchini') || text.includes('bean') || text.includes('vegetable')) return 'vegetable';
      if (text.includes('lavender') || text.includes('marigold') || text.includes('rose') || text.includes('flower') || text.includes('hydrangea')) return 'flower';
      if (text.includes('bush') || text.includes('shrub') || text.includes('blueberry') || text.includes('boxwood') || text.includes('fern')) return 'shrub';
      return 'herb';
    }

    scheduleSave() {
      if (this.saveDebounceTimer) clearTimeout(this.saveDebounceTimer);
      this.saveDebounceTimer = setTimeout(async () => {
        try {
          await fetch('/api/garden/layout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layout: this.layout })
          });
          const ind = document.getElementById('auto-save-indicator');
          if (ind) {
            ind.textContent = 'Saved just now';
            ind.style.opacity = '1';
            setTimeout(() => { ind.style.opacity = '0.6'; }, 2000);
          }
        } catch (e) {
          console.error("Auto-save failed:", e);
        }
      }, 500);
    }

    pushUndo() {
      this.undoStack.push(JSON.parse(JSON.stringify(this.layout)));
      if (this.undoStack.length > 25) this.undoStack.shift();
      this.redoStack = [];
      this.updateUndoRedoButtons();
    }

    undo() {
      if (this.undoStack.length === 0) return;
      this.redoStack.push(JSON.parse(JSON.stringify(this.layout)));
      this.layout = this.undoStack.pop();
      this.scheduleSave();
      this.renderAll();
      this.updateUndoRedoButtons();
    }

    redo() {
      if (this.redoStack.length === 0) return;
      this.undoStack.push(JSON.parse(JSON.stringify(this.layout)));
      this.layout = this.redoStack.pop();
      this.scheduleSave();
      this.renderAll();
      this.updateUndoRedoButtons();
    }

    updateUndoRedoButtons() {
      const btnUndo = document.getElementById('btn-tool-undo');
      const btnRedo = document.getElementById('btn-tool-redo');
      if (btnUndo) btnUndo.disabled = this.undoStack.length === 0;
      if (btnRedo) btnRedo.disabled = this.redoStack.length === 0;
    }

    // --- Master Render Coordinator ---
    renderAll() {
      this.renderLibrary();
      this.renderLegendAndFilters();
      if (this.activeDimension === '2d') {
        this.renderCanvas2D();
      } else {
        this.renderThree3D();
      }
      this.renderSidePanel();
      this.renderListView();
    }

    // --- Library UI ---
    renderLibrary() {
      const container = document.getElementById('garden-library-list');
      if (!container) return;

      const placedIds = new Set(this.layout.plants.map(p => p.id));
      const unplacedPlants = this.plants.filter(p => !placedIds.has(p.id));
      const placedPlants = this.plants.filter(p => placedIds.has(p.id));

      let html = '';

      // Section: Awaiting Placement
      html += `
        <div class="lib-group-title">
          <span>Awaiting Placement</span>
          <span class="lib-count ${unplacedPlants.length > 0 ? 'highlight' : ''}">${unplacedPlants.length}</span>
        </div>
      `;

      if (unplacedPlants.length === 0) {
        html += `<div class="lib-empty">All plants are placed in the garden.</div>`;
      } else {
        html += unplacedPlants.map(p => {
          const condition = p.condition || { badge_label: 'Doing well', color: '#22c55e', icon: 'spa' };
          const isSelected = this.touchPendingPlant && this.touchPendingPlant.id === p.id;
          return `
            <div class="lib-plant-card ${isSelected ? 'touch-selected' : ''}" draggable="true" data-plant-id="${p.id}" onclick="window.gardenPlanner.handleLibraryPlantClick('${p.id}')">
              <div class="lib-plant-icon" style="border-color:${condition.color};">${this.getPlantTypeEmoji(this.inferPlantType(p.name, p.species))}</div>
              <div class="lib-plant-info">
                <div class="lib-plant-name">${p.name}</div>
                <div class="lib-plant-sub">${p.species || 'Species unassigned'}</div>
                <div class="lib-plant-status" style="color:${condition.color};">
                  <span class="material-symbols-outlined status-mini-icon">${condition.icon}</span> ${condition.badge_label}
                </div>
              </div>
              <span class="material-symbols-outlined lib-drag-handle">drag_indicator</span>
            </div>
          `;
        }).join('');
      }

      // Section: Placed in Garden
      html += `
        <div class="lib-group-title" style="margin-top: 1rem;">
          <span>Placed in Garden</span>
          <span class="lib-count">${placedPlants.length}</span>
        </div>
      `;

      html += placedPlants.map(p => {
        const condition = p.condition || { badge_label: 'Doing well', color: '#22c55e', icon: 'spa' };
        const areaName = p.area_name || 'Garden Bed';
        const isSelected = this.selectedPlantId === p.id;
        return `
          <div class="lib-plant-card placed ${isSelected ? 'active-selection' : ''}" onclick="window.gardenPlanner.selectPlant('${p.id}')">
            <div class="lib-plant-icon" style="border-color:${condition.color};">${this.getPlantTypeEmoji(this.inferPlantType(p.name, p.species))}</div>
            <div class="lib-plant-info">
              <div class="lib-plant-name">${p.name}</div>
              <div class="lib-plant-sub">In <strong>${areaName}</strong></div>
              <div class="lib-plant-status" style="color:${condition.color};">
                <span class="material-symbols-outlined status-mini-icon">${condition.icon}</span> ${condition.badge_label}
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Section: Botanical Presets
      html += `
        <div class="lib-group-title" style="margin-top: 1.2rem;">
          <span>Plant Presets Catalog</span>
        </div>
        <div class="preset-grid">
          ${PLANT_PRESETS.map(preset => `
            <div class="preset-chip ${this.touchPendingPlant && this.touchPendingPlant.presetId === preset.id_prefix ? 'touch-selected' : ''}" draggable="true" data-preset-id="${preset.id_prefix}" onclick="window.gardenPlanner.handlePresetClick('${preset.id_prefix}')" title="${preset.description}">
              <span class="preset-emoji">${preset.icon}</span>
              <span class="preset-name">${preset.name}</span>
            </div>
          `).join('')}
        </div>
      `;

      container.innerHTML = html;
      this.bindLibraryDragEvents();
    }

    bindLibraryDragEvents() {
      const cards = document.querySelectorAll('.lib-plant-card[draggable="true"]');
      cards.forEach(card => {
        card.addEventListener('dragstart', (e) => {
          const plantId = card.getAttribute('data-plant-id');
          e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'existing-plant', plantId }));
          this.ghostPlant = { type: 'existing-plant', plantId };
        });
        card.addEventListener('dragend', () => {
          this.ghostPlant = null;
          this.renderCanvas2D();
        });
      });

      const presets = document.querySelectorAll('.preset-chip[draggable="true"]');
      presets.forEach(chip => {
        chip.addEventListener('dragstart', (e) => {
          const presetId = chip.getAttribute('data-preset-id');
          e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'preset', presetId }));
          this.ghostPlant = { type: 'preset', presetId };
        });
        chip.addEventListener('dragend', () => {
          this.ghostPlant = null;
          this.renderCanvas2D();
        });
      });
    }

    handleLibraryPlantClick(plantId) {
      this.touchPendingPlant = { type: 'existing-plant', id: plantId };
      this.renderLibrary();
      this.showToast("Tap any growing area on the canvas to place this plant.");
    }

    handlePresetClick(presetId) {
      this.touchPendingPlant = { type: 'preset', presetId: presetId };
      this.renderLibrary();
      this.showToast("Tap any growing area on the canvas to plant this preset.");
    }

    getPlantTypeEmoji(type) {
      switch (type) {
        case 'herb': return '🌿';
        case 'flower': return '🌸';
        case 'shrub': return '🫐';
        case 'vegetable': return '🍅';
        case 'tree': return '🌳';
        default: return '🌱';
      }
    }

    // --- Legend and Filter Bar ---
    renderLegendAndFilters() {
      const legendContainer = document.getElementById('garden-status-legend');
      if (!legendContainer) return;

      const counts = {
        all: this.plants.length,
        doing_well: 0,
        needs_attention: 0,
        watering_due: 0,
        heat_concern: 0,
        moisture_concern: 0,
        observation_needed: 0
      };

      this.plants.forEach(p => {
        const sc = p.condition ? p.condition.status_code : 'doing_well';
        if (counts[sc] !== undefined) counts[sc]++;
      });

      const pills = [
        { code: 'all', label: 'All Plants', color: '#57606a', count: counts.all, icon: 'grid_view' },
        { code: 'needs_attention', label: 'Needs Attention', color: '#ef4444', count: counts.needs_attention, icon: 'error' },
        { code: 'watering_due', label: 'Watering Due', color: '#0288d1', count: counts.watering_due, icon: 'water_drop' },
        { code: 'heat_concern', label: 'Heat/Dryness', color: '#f59e0b', count: counts.heat_concern, icon: 'thermostat' },
        { code: 'moisture_concern', label: 'Excess Moisture', color: '#06b6d4', count: counts.moisture_concern, icon: 'water_damage' },
        { code: 'observation_needed', label: 'Observation Needed', color: '#8b5cf6', count: counts.observation_needed, icon: 'visibility' },
        { code: 'doing_well', label: 'Doing Well', color: '#22c55e', count: counts.doing_well, icon: 'spa' }
      ];

      legendContainer.innerHTML = pills.map(p => `
        <button class="legend-pill ${this.filterCondition === p.code ? 'active' : ''}" style="--pill-color:${p.color};" onclick="window.gardenPlanner.setConditionFilter('${p.code}')">
          <span class="legend-dot" style="background:${p.color};"></span>
          <span class="material-symbols-outlined pill-icon">${p.icon}</span>
          <span>${p.label}</span>
          <span class="pill-badge">${p.count}</span>
        </button>
      `).join('');

      // Populate area filter dropdown
      const areaSelect = document.getElementById('filter-area-select');
      if (areaSelect) {
        let optHtml = `<option value="all">All Growing Areas (${this.growingAreas.length})</option>`;
        this.growingAreas.forEach(a => {
          optHtml += `<option value="${a.id}" ${this.filterAreaId === a.id ? 'selected' : ''}>${a.name} (${a.area_type})</option>`;
        });
        areaSelect.innerHTML = optHtml;
      }
    }

    setConditionFilter(code) {
      this.filterCondition = code;
      this.renderLegendAndFilters();
      if (this.activeDimension === '2d') this.renderCanvas2D();
      else this.renderThree3D();
      this.renderListView();
    }

    setAreaFilter(areaId) {
      this.filterAreaId = areaId;
      if (this.activeDimension === '2d') this.renderCanvas2D();
      else this.renderThree3D();
      this.renderListView();
    }

    // --- 2D Canvas Setup & Events ---
    setupCanvas2D() {
      if (!this.canvas) return;

      const resize = () => {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.canvas.style.width = `${rect.width}px`;
        this.canvas.style.height = `${rect.height}px`;
        this.renderCanvas2D();
      };

      window.addEventListener('resize', resize);
      setTimeout(resize, 50);

      // Mouse & Pointer events on 2D Canvas
      this.canvas.addEventListener('mousedown', (e) => this.handleCanvasMouseDown(e));
      this.canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));
      window.addEventListener('mouseup', (e) => this.handleCanvasMouseUp(e));
      this.canvas.addEventListener('wheel', (e) => this.handleCanvasWheel(e), { passive: false });

      // Drag and drop onto 2D Canvas
      this.canvas.addEventListener('dragover', (e) => this.handleCanvasDragOver(e));
      this.canvas.addEventListener('dragleave', (e) => this.handleCanvasDragLeave(e));
      this.canvas.addEventListener('drop', (e) => this.handleCanvasDrop(e));

      // Touch events for mobile
      this.canvas.addEventListener('touchstart', (e) => this.handleCanvasTouchStart(e), { passive: false });
      this.canvas.addEventListener('touchmove', (e) => this.handleCanvasTouchMove(e), { passive: false });
      this.canvas.addEventListener('touchend', (e) => this.handleCanvasTouchEnd(e));
    }

    screenToWorld(screenX, screenY) {
      const rect = this.canvas.getBoundingClientRect();
      const x = (screenX - rect.left - this.panX) / this.zoom;
      const y = (screenY - rect.top - this.panY) / this.zoom;
      return { x, y };
    }

    worldToScreen(worldX, worldY) {
      const rect = this.canvas.getBoundingClientRect();
      const x = worldX * this.zoom + this.panX + rect.left;
      const y = worldY * this.zoom + this.panY + rect.top;
      return { x, y };
    }

    handleCanvasWheel(e) {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const mouse = this.screenToWorld(e.clientX, e.clientY);

      const newZoom = Math.max(0.3, Math.min(3.0, this.zoom * zoomFactor));
      this.panX -= (mouse.x * newZoom - mouse.x * this.zoom);
      this.panY -= (mouse.y * newZoom - mouse.y * this.zoom);
      this.zoom = newZoom;

      this.renderCanvas2D();
    }

    handleCanvasMouseDown(e) {
      if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
        this.isPanning = true;
        this.panStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
        return;
      }

      if (e.button !== 0) return;
      const mouse = this.screenToWorld(e.clientX, e.clientY);

      if (this.touchPendingPlant) {
        this.placePendingPlantAt(mouse);
        return;
      }

      if (this.activeMode === 'explore') {
        const clickedPlant = this.hitTestPlant(mouse);
        if (clickedPlant) {
          this.selectPlant(clickedPlant.id);
        } else {
          const clickedArea = this.hitTestArea(mouse);
          if (clickedArea) {
            this.selectArea(clickedArea.id);
          } else {
            this.clearSelection();
          }
        }
        this.renderCanvas2D();
        return;
      }

      // EDIT MODE:
      if (this.activeTool === 'freehand') {
        this.isDrawing = true;
        this.freehandPoints = [mouse];
      } else if (this.activeTool === 'rect') {
        this.isDrawing = true;
        this.rectStart = mouse;
        this.rectCurrent = mouse;
      } else if (this.activeTool === 'polygon') {
        if (this.polygonPoints.length === 0) {
          this.polygonPoints.push(mouse);
        } else {
          const startPt = this.polygonPoints[0];
          if (Geometry.distance(mouse, startPt) < 18 / this.zoom && this.polygonPoints.length >= 3) {
            this.finishPolygonArea();
          } else {
            this.polygonPoints.push(mouse);
          }
        }
        this.renderCanvas2D();
      } else if (this.activeTool === 'select') {
        if (this.selectedAreaId) {
          const area = this.layout.areas.find(a => a.id === this.selectedAreaId);
          if (area) {
            for (let i = 0; i < area.points.length; i++) {
              if (Geometry.distance(mouse, area.points[i]) < 12 / this.zoom) {
                this.pushUndo();
                this.isDraggingObject = true;
                this.dragTargetType = 'vertex';
                this.dragVertexIndex = i;
                return;
              }
            }
          }
        }

        const hitPlant = this.hitTestPlant(mouse);
        if (hitPlant) {
          this.pushUndo();
          this.selectPlant(hitPlant.id);
          this.isDraggingObject = true;
          this.dragTargetType = 'plant';
          this.dragStartWorld = { x: mouse.x - hitPlant.x, y: mouse.y - hitPlant.y };
          this.renderCanvas2D();
          return;
        }

        const hitArea = this.hitTestArea(mouse);
        if (hitArea) {
          this.pushUndo();
          this.selectArea(hitArea.id);
          this.isDraggingObject = true;
          this.dragTargetType = 'area';
          this.dragStartWorld = { x: mouse.x, y: mouse.y };
          this.renderCanvas2D();
          return;
        }

        this.clearSelection();
        this.isPanning = true;
        this.panStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
        this.renderCanvas2D();
      }
    }

    handleCanvasMouseMove(e) {
      if (this.isPanning) {
        this.panX = e.clientX - this.panStart.x;
        this.panY = e.clientY - this.panStart.y;
        this.renderCanvas2D();
        return;
      }

      const mouse = this.screenToWorld(e.clientX, e.clientY);

      if (this.isDrawing) {
        if (this.activeTool === 'freehand') {
          const lastPt = this.freehandPoints[this.freehandPoints.length - 1];
          if (Geometry.distance(mouse, lastPt) > 4 / this.zoom) {
            this.freehandPoints.push(mouse);
            this.renderCanvas2D();
          }
        } else if (this.activeTool === 'rect') {
          this.rectCurrent = mouse;
          this.renderCanvas2D();
        }
      } else if (this.isDraggingObject) {
        if (this.dragTargetType === 'plant' && this.selectedPlantId) {
          const plant = this.layout.plants.find(p => p.id === this.selectedPlantId);
          if (plant) {
            plant.x = mouse.x - this.dragStartWorld.x;
            plant.y = mouse.y - this.dragStartWorld.y;

            const destArea = this.findAreaContainingPoint({ x: plant.x, y: plant.y });
            this.hoveredAreaId = destArea ? destArea.id : null;
            this.renderCanvas2D();
          }
        } else if (this.dragTargetType === 'area' && this.selectedAreaId) {
          const area = this.layout.areas.find(a => a.id === this.selectedAreaId);
          if (area) {
            const dx = mouse.x - this.dragStartWorld.x;
            const dy = mouse.y - this.dragStartWorld.y;
            this.dragStartWorld = { x: mouse.x, y: mouse.y };

            area.points.forEach(p => {
              p.x += dx;
              p.y += dy;
            });

            this.layout.plants.forEach(p => {
              if (p.area_id === area.id) {
                p.x += dx;
                p.y += dy;
              }
            });

            this.renderCanvas2D();
          }
        } else if (this.dragTargetType === 'vertex' && this.selectedAreaId && this.dragVertexIndex >= 0) {
          const area = this.layout.areas.find(a => a.id === this.selectedAreaId);
          if (area && area.points[this.dragVertexIndex]) {
            area.points[this.dragVertexIndex].x = mouse.x;
            area.points[this.dragVertexIndex].y = mouse.y;
            this.renderCanvas2D();
          }
        }
      } else if (this.activeTool === 'polygon' && this.polygonPoints.length > 0) {
        this.renderCanvas2D(mouse);
      }
    }

    handleCanvasMouseUp(e) {
      if (this.isPanning) {
        this.isPanning = false;
      }

      if (this.isDrawing) {
        if (this.activeTool === 'freehand') {
          this.isDrawing = false;
          if (this.freehandPoints.length >= 6) {
            this.finishFreehandArea();
          }
          this.freehandPoints = [];
        } else if (this.activeTool === 'rect' && this.rectStart && this.rectCurrent) {
          this.isDrawing = false;
          this.finishRectArea();
          this.rectStart = null;
          this.rectCurrent = null;
        }
      }

      if (this.isDraggingObject) {
        if (this.dragTargetType === 'plant' && this.selectedPlantId) {
          const plant = this.layout.plants.find(p => p.id === this.selectedPlantId);
          if (plant) {
            const destArea = this.findAreaContainingPoint({ x: plant.x, y: plant.y });
            if (destArea && destArea.id !== plant.area_id) {
              this.reassignPlantArea(plant.id, destArea.id);
            }
          }
        }
        this.isDraggingObject = false;
        this.dragTargetType = null;
        this.hoveredAreaId = null;
        this.scheduleSave();
        this.renderAll();
      }
    }

    // Touch event handlers for mobile
    handleCanvasTouchStart(e) {
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        this.handleCanvasMouseDown({
          button: 0,
          clientX: touch.clientX,
          clientY: touch.clientY,
          shiftKey: false
        });
      } else if (e.touches.length === 2) {
        e.preventDefault();
        this.isPinching = true;
        this.pinchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    }

    handleCanvasTouchMove(e) {
      if (this.isPinching && e.touches.length === 2) {
        e.preventDefault();
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / this.pinchDist;
        this.zoom = Math.max(0.3, Math.min(3.0, this.zoom * factor));
        this.pinchDist = dist;
        this.renderCanvas2D();
      } else if (e.touches.length === 1) {
        const touch = e.touches[0];
        this.handleCanvasMouseMove({
          clientX: touch.clientX,
          clientY: touch.clientY
        });
      }
    }

    handleCanvasTouchEnd(e) {
      this.isPinching = false;
      this.handleCanvasMouseUp({});
    }

    // --- Drag and Drop into Canvas ---
    handleCanvasDragOver(e) {
      e.preventDefault();
      const mouse = this.screenToWorld(e.clientX, e.clientY);
      const destArea = this.findAreaContainingPoint(mouse);
      this.hoveredAreaId = destArea ? destArea.id : null;
      this.dragHoverCoord = mouse;
      this.renderCanvas2D();
    }

    handleCanvasDragLeave(e) {
      this.hoveredAreaId = null;
      this.dragHoverCoord = null;
      this.renderCanvas2D();
    }

    async handleCanvasDrop(e) {
      e.preventDefault();
      this.hoveredAreaId = null;
      this.dragHoverCoord = null;

      const dataStr = e.dataTransfer.getData('text/plain');
      if (!dataStr) return;

      try {
        const payload = JSON.parse(dataStr);
        const mouse = this.screenToWorld(e.clientX, e.clientY);
        const destArea = this.findAreaContainingPoint(mouse) || (this.layout.areas[0] || null);

        if (!destArea) {
          this.showToast("Please draw a growing area first before placing plants!");
          return;
        }

        if (payload.type === 'existing-plant') {
          this.placeExistingPlant(payload.plantId, destArea.id, mouse.x, mouse.y);
        } else if (payload.type === 'preset') {
          await this.createPlantFromPreset(payload.presetId, destArea.id, mouse.x, mouse.y);
        }
      } catch (err) {
        console.error("Drop error:", err);
      }
    }

    placePendingPlantAt(worldCoord) {
      const destArea = this.findAreaContainingPoint(worldCoord) || (this.layout.areas[0] || null);
      if (!destArea) {
        this.showToast("Please tap inside a growing area to place the plant.");
        return;
      }

      if (this.touchPendingPlant.type === 'existing-plant') {
        this.placeExistingPlant(this.touchPendingPlant.id, destArea.id, worldCoord.x, worldCoord.y);
      } else if (this.touchPendingPlant.type === 'preset') {
        this.createPlantFromPreset(this.touchPendingPlant.presetId, destArea.id, worldCoord.x, worldCoord.y);
      }

      this.touchPendingPlant = null;
      this.renderLibrary();
    }

    placeExistingPlant(plantId, areaId, x, y) {
      this.pushUndo();

      let lp = this.layout.plants.find(p => p.id === plantId);
      if (lp) {
        lp.x = x;
        lp.y = y;
        lp.area_id = areaId;
      } else {
        const dbPlant = this.plants.find(p => p.id === plantId);
        lp = {
          id: plantId,
          area_id: areaId,
          name: dbPlant ? dbPlant.name : 'Plant',
          plant_type: dbPlant ? this.inferPlantType(dbPlant.name, dbPlant.species) : 'herb',
          x: x,
          y: y,
          scale: 1.0,
          rotation: 0,
          planting_type: dbPlant ? dbPlant.planting_type : 'container'
        };
        this.layout.plants.push(lp);
      }

      this.reassignPlantArea(plantId, areaId);
      this.selectPlant(plantId);
      this.scheduleSave();
      this.renderAll();
      this.showToast(`Placed ${lp.name} in ${this.getAreaName(areaId)}.`);
    }

    async createPlantFromPreset(presetId, areaId, x, y) {
      const preset = PLANT_PRESETS.find(p => p.id_prefix === presetId);
      if (!preset) return;

      this.pushUndo();

      try {
        const res = await fetch('/api/plants', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            area_id: areaId,
            name: preset.name,
            species: preset.species,
            planting_type: preset.planting_type,
            container_size_liters: preset.container_size_liters,
            substrate_type: preset.substrate_type,
            drainage_quality: preset.drainage_quality
          })
        });

        const data = await res.json();
        const createdPlant = data.plant;

        if (createdPlant) {
          this.plants.push(createdPlant);
          this.layout.plants.push({
            id: createdPlant.id,
            area_id: areaId,
            name: createdPlant.name,
            plant_type: preset.plant_type,
            x: x,
            y: y,
            scale: 1.0,
            rotation: 0,
            planting_type: createdPlant.planting_type
          });

          this.selectPlant(createdPlant.id);
          this.scheduleSave();
          this.renderAll();
          this.showToast(`Planted new ${preset.name}!`);
        }
      } catch (err) {
        console.error("Failed to create plant preset:", err);
      }
    }

    async reassignPlantArea(plantId, newAreaId) {
      try {
        await fetch(`/api/plants/${plantId}/area`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ area_id: newAreaId })
        });

        const p = this.plants.find(dp => dp.id === plantId);
        if (p) {
          p.area_id = newAreaId;
          const a = this.growingAreas.find(ga => ga.id === newAreaId);
          if (a) {
            p.area_name = a.name;
            p.shelter_from_rain = a.shelter_from_rain;
            p.sun_exposure = a.sun_exposure;
          }
        }
      } catch (err) {
        console.error("Failed to reassign plant area:", err);
      }
    }

    // --- Shape Creation & Smoothing ---
    finishFreehandArea() {
      const reduced = Geometry.douglasPeucker(this.freehandPoints, 8 / this.zoom);
      if (reduced.length < 3) return;
      const smoothed = Geometry.chaikinSmooth(reduced, 2);
      this.openAreaModalWithPoints(smoothed, 'freehand');
    }

    finishRectArea() {
      const x1 = Math.min(this.rectStart.x, this.rectCurrent.x);
      const y1 = Math.min(this.rectStart.y, this.rectCurrent.y);
      const x2 = Math.max(this.rectStart.x, this.rectCurrent.x);
      const y2 = Math.max(this.rectStart.y, this.rectCurrent.y);

      if (x2 - x1 < 20 || y2 - y1 < 20) return;

      const points = [
        { x: x1, y: y1 },
        { x: x2, y: y1 },
        { x: x2, y: y2 },
        { x: x1, y: y2 }
      ];

      this.openAreaModalWithPoints(points, 'rectangle');
    }

    finishPolygonArea() {
      if (this.polygonPoints.length < 3) return;
      const points = this.polygonPoints.slice();
      this.polygonPoints = [];
      this.openAreaModalWithPoints(points, 'polygon');
    }

    openAreaModalWithPoints(points, shapeType) {
      this.pendingAreaPoints = points;
      this.pendingShapeType = shapeType;

      const modal = document.getElementById('modal-area-create');
      if (modal) {
        document.getElementById('area-form-name').value = `Growing Area ${this.layout.areas.length + 1}`;
        document.getElementById('area-form-type').value = 'raised bed';
        document.getElementById('area-form-sun').value = 'full sun';
        document.getElementById('area-form-shelter').value = '0';
        modal.style.display = 'flex';
      }
    }

    async submitNewArea() {
      const name = document.getElementById('area-form-name').value.trim() || 'New Area';
      const areaType = document.getElementById('area-form-type').value;
      const sun = document.getElementById('area-form-sun').value;
      const shelter = document.getElementById('area-form-shelter').value === '1';
      const watering = document.getElementById('area-form-watering').value.trim();

      try {
        const res = await fetch('/api/areas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name,
            area_type: areaType,
            sun_exposure: sun,
            shelter_from_rain: shelter,
            watering_arrangements: watering
          })
        });

        const data = await res.json();
        const newArea = data.growing_area;

        if (newArea) {
          this.growingAreas.push(newArea);
          this.pushUndo();

          this.layout.areas.push({
            id: newArea.id,
            name: newArea.name,
            area_type: newArea.area_type,
            shape_type: this.pendingShapeType || 'polygon',
            points: this.pendingAreaPoints,
            rotation: 0
          });

          this.selectArea(newArea.id);
          this.scheduleSave();
          this.renderAll();
          this.closeAreaModal();
          this.showToast(`Created growing area "${name}".`);
        }
      } catch (err) {
        console.error("Failed to add area:", err);
      }
    }

    closeAreaModal() {
      const modal = document.getElementById('modal-area-create');
      if (modal) modal.style.display = 'none';
      this.pendingAreaPoints = null;
      this.setTool('select');
    }

    // --- Hit Testing ---
    hitTestPlant(point) {
      for (let i = this.layout.plants.length - 1; i >= 0; i--) {
        const p = this.layout.plants[i];
        const radius = 24 * (p.scale || 1.0);
        if (Geometry.distance(point, { x: p.x, y: p.y }) <= radius) {
          return p;
        }
      }
      return null;
    }

    hitTestArea(point) {
      for (let i = this.layout.areas.length - 1; i >= 0; i--) {
        const a = this.layout.areas[i];
        if (Geometry.pointInPolygon(point, a.points)) {
          return a;
        }
      }
      return null;
    }

    findAreaContainingPoint(point) {
      return this.hitTestArea(point);
    }

    getAreaName(areaId) {
      const a = this.growingAreas.find(ga => ga.id === areaId);
      return a ? a.name : 'Unknown Area';
    }

    selectPlant(plantId) {
      this.selectedPlantId = plantId;
      this.selectedAreaId = null;
      this.renderAll();
    }

    selectArea(areaId) {
      this.selectedAreaId = areaId;
      this.selectedPlantId = null;
      this.renderAll();
    }

    clearSelection() {
      this.selectedPlantId = null;
      this.selectedAreaId = null;
      this.renderAll();
    }

    // --- 2D Rendering Engine ---
    renderCanvas2D(cursorHint = null) {
      if (!this.ctx || !this.canvas) return;

      const ctx = this.ctx;
      const width = this.canvas.width / (window.devicePixelRatio || 1);
      const height = this.canvas.height / (window.devicePixelRatio || 1);

      ctx.save();
      ctx.clearRect(0, 0, width, height);

      // Apply Pan & Zoom
      ctx.translate(this.panX, this.panY);
      ctx.scale(this.zoom, this.zoom);

      // Draw subtle background grid
      this.drawGrid(ctx, width, height);

      // Draw Growing Areas
      this.layout.areas.forEach(area => {
        this.drawArea2D(ctx, area);
      });

      // Draw Plants
      this.layout.plants.forEach(plant => {
        this.drawPlant2D(ctx, plant);
      });

      // Draw Ghost Drag Preview
      if (this.dragHoverCoord) {
        ctx.save();
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.arc(this.dragHoverCoord.x, this.dragHoverCoord.y, 25, 0, Math.PI * 2);
        ctx.fillStyle = '#2e7d32';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.restore();
      }

      // Draw Active In-Progress Freehand Stroke
      if (this.isDrawing && this.activeTool === 'freehand' && this.freehandPoints.length > 1) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(this.freehandPoints[0].x, this.freehandPoints[0].y);
        for (let i = 1; i < this.freehandPoints.length; i++) {
          ctx.lineTo(this.freehandPoints[i].x, this.freehandPoints[i].y);
        }
        ctx.strokeStyle = '#2e7d32';
        ctx.lineWidth = 3 / this.zoom;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();
        ctx.restore();
      }

      // Draw Active In-Progress Rectangle
      if (this.isDrawing && this.activeTool === 'rect' && this.rectStart && this.rectCurrent) {
        ctx.save();
        const rx = Math.min(this.rectStart.x, this.rectCurrent.x);
        const ry = Math.min(this.rectStart.y, this.rectCurrent.y);
        const rw = Math.abs(this.rectCurrent.x - this.rectStart.x);
        const rh = Math.abs(this.rectCurrent.y - this.rectStart.y);

        ctx.fillStyle = 'rgba(46, 125, 50, 0.15)';
        ctx.fillRect(rx, ry, rw, rh);
        ctx.strokeStyle = '#2e7d32';
        ctx.lineWidth = 2 / this.zoom;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(rx, ry, rw, rh);
        ctx.restore();
      }

      // Draw Active In-Progress Polygon
      if (this.activeTool === 'polygon' && this.polygonPoints.length > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(this.polygonPoints[0].x, this.polygonPoints[0].y);
        for (let i = 1; i < this.polygonPoints.length; i++) {
          ctx.lineTo(this.polygonPoints[i].x, this.polygonPoints[i].y);
        }
        if (cursorHint) {
          ctx.lineTo(cursorHint.x, cursorHint.y);
        }
        ctx.strokeStyle = '#2e7d32';
        ctx.lineWidth = 2 / this.zoom;
        ctx.stroke();

        this.polygonPoints.forEach((pt, idx) => {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, (idx === 0 ? 6 : 4) / this.zoom, 0, Math.PI * 2);
          ctx.fillStyle = idx === 0 ? '#d32f2f' : '#2e7d32';
          ctx.fill();
        });
        ctx.restore();
      }

      ctx.restore();
    }

    drawGrid(ctx, width, height) {
      const gridSize = 40;
      const startX = Math.floor(-this.panX / this.zoom / gridSize) * gridSize - gridSize;
      const startY = Math.floor(-this.panY / this.zoom / gridSize) * gridSize - gridSize;
      const endX = startX + (width / this.zoom) + gridSize * 2;
      const endY = startY + (height / this.zoom) + gridSize * 2;

      ctx.save();
      ctx.strokeStyle = 'rgba(208, 215, 222, 0.45)';
      ctx.lineWidth = 1 / this.zoom;

      ctx.beginPath();
      for (let x = startX; x <= endX; x += gridSize) {
        ctx.moveTo(x, startY);
        ctx.lineTo(x, endY);
      }
      for (let y = startY; y <= endY; y += gridSize) {
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
      }
      ctx.stroke();
      ctx.restore();
    }

    drawArea2D(ctx, area) {
      if (!area.points || area.points.length < 3) return;

      const isSelected = this.selectedAreaId === area.id;
      const isHovered = this.hoveredAreaId === area.id;

      ctx.save();

      ctx.beginPath();
      ctx.moveTo(area.points[0].x, area.points[0].y);
      for (let i = 1; i < area.points.length; i++) {
        ctx.lineTo(area.points[i].x, area.points[i].y);
      }
      ctx.closePath();

      const type = (area.area_type || 'balcony').toLowerCase();
      let fillColor = '#ffffff';
      let strokeColor = '#8d6e63';
      let strokeWidth = 3;

      if (type.includes('balcony')) {
        fillColor = '#f5efe6';
        strokeColor = '#a1887f';
        strokeWidth = 3;
      } else if (type.includes('patio')) {
        fillColor = '#eaecef';
        strokeColor = '#94a3b8';
        strokeWidth = 3;
      } else if (type.includes('raised')) {
        fillColor = '#3e2723';
        strokeColor = '#8d5b4c';
        strokeWidth = 6;
      } else if (type.includes('lawn')) {
        fillColor = '#dcfce7';
        strokeColor = '#22c55e';
        strokeWidth = 2;
      } else if (type.includes('greenhouse')) {
        fillColor = 'rgba(224, 242, 254, 0.7)';
        strokeColor = '#0288d1';
        strokeWidth = 3;
      } else {
        fillColor = '#4e342e';
        strokeColor = '#795548';
        strokeWidth = 4;
      }

      ctx.shadowColor = 'rgba(0, 0, 0, 0.08)';
      ctx.shadowBlur = 12 * this.zoom;
      ctx.shadowOffsetY = 4 * this.zoom;

      ctx.fillStyle = fillColor;
      ctx.fill();

      ctx.shadowColor = 'transparent';
      this.drawAreaTexture2D(ctx, area, type);

      ctx.strokeStyle = isHovered ? '#10b981' : (isSelected ? '#2e7d32' : strokeColor);
      ctx.lineWidth = (isSelected || isHovered ? strokeWidth + 2 : strokeWidth) / this.zoom;
      ctx.stroke();

      if (isSelected && this.activeMode === 'edit') {
        area.points.forEach((p) => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 5 / this.zoom, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.fill();
          ctx.strokeStyle = '#2e7d32';
          ctx.lineWidth = 2 / this.zoom;
          ctx.stroke();
        });
      }

      // Centroid label
      const centroid = Geometry.polygonCentroid(area.points);
      ctx.save();
      ctx.font = `600 ${11 / this.zoom}px -apple-system, sans-serif`;
      const labelText = `${area.name} (${area.area_type || 'area'})`;
      const textWidth = ctx.measureText(labelText).width;
      const badgeW = textWidth + 20 / this.zoom;
      const badgeH = 18 / this.zoom;

      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.strokeStyle = 'rgba(0,0,0,0.15)';
      ctx.lineWidth = 1 / this.zoom;
      ctx.beginPath();
      ctx.roundRect(centroid.x - badgeW / 2, centroid.y - badgeH / 2, badgeW, badgeH, 4 / this.zoom);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#24292f';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, centroid.x, centroid.y);
      ctx.restore();

      ctx.restore();
    }

    drawAreaTexture2D(ctx, area, type) {
      const bounds = Geometry.polygonBounds(area.points);
      ctx.save();
      ctx.clip();

      if (type.includes('balcony')) {
        ctx.strokeStyle = 'rgba(141, 110, 99, 0.2)';
        ctx.lineWidth = 1.5 / this.zoom;
        for (let y = bounds.minY; y <= bounds.maxY; y += 22) {
          ctx.beginPath();
          ctx.moveTo(bounds.minX, y);
          ctx.lineTo(bounds.maxX, y);
          ctx.stroke();
        }
      } else if (type.includes('patio')) {
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
        ctx.lineWidth = 1.5 / this.zoom;
        for (let x = bounds.minX; x <= bounds.maxX; x += 32) {
          ctx.beginPath();
          ctx.moveTo(x, bounds.minY);
          ctx.lineTo(x, bounds.maxY);
          ctx.stroke();
        }
        for (let y = bounds.minY; y <= bounds.maxY; y += 32) {
          ctx.beginPath();
          ctx.moveTo(bounds.minX, y);
          ctx.lineTo(bounds.maxX, y);
          ctx.stroke();
        }
      } else if (type.includes('lawn')) {
        ctx.strokeStyle = 'rgba(34, 197, 94, 0.25)';
        ctx.lineWidth = 1 / this.zoom;
        for (let x = bounds.minX + 8; x <= bounds.maxX; x += 20) {
          for (let y = bounds.minY + 8; y <= bounds.maxY; y += 20) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x + 3, y - 6);
            ctx.stroke();
          }
        }
      }
      ctx.restore();
    }

    drawPlant2D(ctx, plant) {
      const isSelected = this.selectedPlantId === plant.id;
      const dbPlant = this.plants.find(p => p.id === plant.id);
      const condition = dbPlant ? (dbPlant.condition || { color: '#22c55e', icon: 'spa' }) : { color: '#22c55e', icon: 'spa' };

      const matchesCondition = this.filterCondition === 'all' || (dbPlant && dbPlant.condition && dbPlant.condition.status_code === this.filterCondition);
      const matchesArea = this.filterAreaId === 'all' || (plant.area_id === this.filterAreaId);
      const isDimmed = !matchesCondition || !matchesArea;

      ctx.save();
      ctx.translate(plant.x, plant.y);
      ctx.scale(plant.scale || 1.0, plant.scale || 1.0);
      ctx.rotate((plant.rotation || 0) * Math.PI / 180);

      if (isDimmed) {
        ctx.globalAlpha = 0.25;
      }

      const pType = plant.plant_type || 'herb';
      const isContainer = (plant.planting_type || 'container') === 'container';

      if (isContainer) {
        ctx.beginPath();
        ctx.arc(0, 0, 19, 0, Math.PI * 2);
        ctx.fillStyle = '#b45309';
        ctx.fill();
        ctx.strokeStyle = '#78350f';
        ctx.lineWidth = 2.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(0, 0, 15, 0, Math.PI * 2);
        ctx.fillStyle = '#3f2e22';
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, 17, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(78, 52, 46, 0.45)';
        ctx.fill();
      }

      this.drawBotanicalFoliage2D(ctx, pType);

      ctx.beginPath();
      ctx.arc(0, 0, 23, 0, Math.PI * 2);
      ctx.strokeStyle = condition.color || '#22c55e';
      ctx.lineWidth = isSelected ? 4 : 2.5;
      ctx.stroke();

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(0, 0, 28, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(46, 125, 50, 0.4)';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
        ctx.stroke();
      }

      // Status indicator badge
      ctx.save();
      ctx.translate(14, -14);
      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, Math.PI * 2);
      ctx.fillStyle = condition.color || '#22c55e';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      // Plant name
      ctx.save();
      ctx.font = `600 ${10 / this.zoom}px -apple-system, sans-serif`;
      const name = plant.name || 'Plant';
      const tw = ctx.measureText(name).width;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
      ctx.beginPath();
      ctx.roundRect(-tw / 2 - 4, 25, tw + 8, 14, 3);
      ctx.fill();

      ctx.fillStyle = '#24292f';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(name, 0, 32);
      ctx.restore();

      ctx.restore();
    }

    drawBotanicalFoliage2D(ctx, type) {
      ctx.save();
      if (type === 'herb') {
        ctx.fillStyle = '#16a34a';
        for (let i = 0; i < 6; i++) {
          const angle = (i * Math.PI) / 3;
          ctx.beginPath();
          ctx.ellipse(Math.cos(angle) * 7, Math.sin(angle) * 7, 7, 4, angle, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(0, 0, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#22c55e';
        ctx.fill();
      } else if (type === 'flower') {
        ctx.fillStyle = '#15803d';
        for (let i = 0; i < 4; i++) {
          const angle = (i * Math.PI) / 2 + 0.3;
          ctx.beginPath();
          ctx.ellipse(Math.cos(angle) * 8, Math.sin(angle) * 8, 6, 3, angle, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = '#ec4899';
        for (let i = 0; i < 5; i++) {
          const angle = (i * Math.PI * 2) / 5;
          ctx.beginPath();
          ctx.arc(Math.cos(angle) * 5, Math.sin(angle) * 5, 4.5, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(0, 0, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#facc15';
        ctx.fill();
      } else if (type === 'shrub') {
        ctx.fillStyle = '#166534';
        const clusters = [
          { x: -5, y: -4, r: 8 }, { x: 5, y: -4, r: 8 },
          { x: -4, y: 5, r: 8 }, { x: 4, y: 5, r: 8 }, { x: 0, y: 0, r: 9 }
        ];
        clusters.forEach(c => {
          ctx.beginPath();
          ctx.arc(c.x, c.y, c.r, 0, Math.PI * 2);
          ctx.fill();
        });
        ctx.fillStyle = '#38bdf8';
        [[-4, -3], [5, 2], [1, -5]].forEach(([bx, by]) => {
          ctx.beginPath();
          ctx.arc(bx, by, 1.8, 0, Math.PI * 2);
          ctx.fill();
        });
      } else if (type === 'vegetable') {
        ctx.fillStyle = '#22c55e';
        for (let i = 0; i < 4; i++) {
          const angle = (i * Math.PI) / 2;
          ctx.beginPath();
          ctx.ellipse(Math.cos(angle) * 9, Math.sin(angle) * 9, 8, 5, angle, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(-2, -2, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(4, 3, 4, 0, Math.PI * 2);
        ctx.fill();
      } else if (type === 'tree') {
        ctx.fillStyle = '#14532d';
        ctx.beginPath();
        ctx.arc(0, 0, 16, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#16a34a';
        ctx.beginPath();
        ctx.arc(-3, -3, 11, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#78350f';
        ctx.beginPath();
        ctx.arc(0, 0, 4, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    // --- 3D Three.js WebGL Engine ---
    setupThree3D() {
      if (!this.threeContainer || typeof THREE === 'undefined') return;

      const rect = this.threeContainer.getBoundingClientRect();
      const width = rect.width || 800;
      const height = rect.height || 600;

      this.threeScene = new THREE.Scene();
      this.threeScene.background = new THREE.Color(0xf4f6f8);

      const aspect = width / height;
      const d = 350;
      this.threeCamera = new THREE.OrthographicCamera(
        -d * aspect, d * aspect,
        d, -d,
        1, 3000
      );
      this.threeCamera.position.set(400, 450, 400);
      this.threeCamera.lookAt(200, 0, 150);

      this.threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.threeRenderer.setSize(width, height);
      this.threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.threeRenderer.shadowMap.enabled = true;
      this.threeRenderer.shadowMap.type = THREE.PCFSoftShadowMap;

      this.threeContainer.innerHTML = '';
      this.threeContainer.appendChild(this.threeRenderer.domElement);

      if (typeof THREE.OrbitControls !== 'undefined') {
        this.threeControls = new THREE.OrbitControls(this.threeCamera, this.threeRenderer.domElement);
        this.threeControls.enableDamping = true;
        this.threeControls.dampingFactor = 0.05;
        this.threeControls.target.set(200, 0, 150);
        this.threeControls.maxPolarAngle = Math.PI / 2.1;
      }

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
      this.threeScene.add(ambientLight);

      const hemiLight = new THREE.HemisphereLight(0xfff8e7, 0x556b2f, 0.4);
      this.threeScene.add(hemiLight);

      const sunLight = new THREE.DirectionalLight(0xfffaed, 0.9);
      sunLight.position.set(250, 500, 200);
      sunLight.castShadow = true;
      sunLight.shadow.mapSize.width = 2048;
      sunLight.shadow.mapSize.height = 2048;
      sunLight.shadow.camera.near = 50;
      sunLight.shadow.camera.far = 1200;
      const shadowD = 600;
      sunLight.shadow.camera.left = -shadowD;
      sunLight.shadow.camera.right = shadowD;
      sunLight.shadow.camera.top = shadowD;
      sunLight.shadow.camera.bottom = -shadowD;
      this.threeScene.add(sunLight);

      const groundGeo = new THREE.PlaneGeometry(2500, 2500);
      const groundMat = new THREE.MeshLambertMaterial({ color: 0xebedf0 });
      const ground = new THREE.Mesh(groundGeo, groundMat);
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = -2;
      ground.receiveShadow = true;
      this.threeScene.add(ground);

      this.threeRaycaster = new THREE.Raycaster();
      this.threeMouse = new THREE.Vector2();

      this.threeRenderer.domElement.addEventListener('click', (e) => this.handleThreeClick(e));

      const animate = () => {
        requestAnimationFrame(animate);
        if (this.threeControls) this.threeControls.update();
        if (this.threeRenderer && this.threeScene && this.threeCamera) {
          this.threeRenderer.render(this.threeScene, this.threeCamera);
        }
      };
      animate();

      window.addEventListener('resize', () => {
        if (!this.threeContainer || !this.threeCamera || !this.threeRenderer) return;
        const r = this.threeContainer.getBoundingClientRect();
        const asp = r.width / r.height;
        this.threeCamera.left = -d * asp;
        this.threeCamera.right = d * asp;
        this.threeCamera.top = d;
        this.threeCamera.bottom = -d;
        this.threeCamera.updateProjectionMatrix();
        this.threeRenderer.setSize(r.width, r.height);
      });
    }

    renderThree3D() {
      if (!this.threeScene || typeof THREE === 'undefined') return;

      Object.values(this.threeAreaMeshes).forEach(m => this.threeScene.remove(m));
      Object.values(this.threePlantMeshes).forEach(m => this.threeScene.remove(m));
      this.threeAreaMeshes = {};
      this.threePlantMeshes = {};

      this.layout.areas.forEach(area => {
        if (!area.points || area.points.length < 3) return;

        const shape = new THREE.Shape();
        shape.moveTo(area.points[0].x, area.points[0].y);
        for (let i = 1; i < area.points.length; i++) {
          shape.lineTo(area.points[i].x, area.points[i].y);
        }
        shape.closePath();

        const type = (area.area_type || 'balcony').toLowerCase();
        let extrudeDepth = 8;
        let color = 0xd7ccc8;

        if (type.includes('raised')) {
          extrudeDepth = 22;
          color = 0x8d5b4c;
        } else if (type.includes('balcony')) {
          extrudeDepth = 10;
          color = 0xd7ccc8;
        } else if (type.includes('patio')) {
          extrudeDepth = 6;
          color = 0x94a3b8;
        } else if (type.includes('lawn')) {
          extrudeDepth = 4;
          color = 0x4ade80;
        } else if (type.includes('greenhouse')) {
          extrudeDepth = 6;
          color = 0x38bdf8;
        }

        const extrudeSettings = {
          steps: 1,
          depth: extrudeDepth,
          bevelEnabled: true,
          bevelThickness: 2,
          bevelSize: 1.5,
          bevelSegments: 2
        };

        const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        geom.rotateX(Math.PI / 2);

        const mat = new THREE.MeshStandardMaterial({
          color: color,
          roughness: 0.8,
          metalness: 0.1
        });

        const mesh = new THREE.Mesh(geom, mat);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData = { type: 'area', areaId: area.id };

        this.threeScene.add(mesh);
        this.threeAreaMeshes[area.id] = mesh;
      });

      this.layout.plants.forEach(plant => {
        const group = new THREE.Group();
        group.position.set(plant.x, 0, plant.y);

        const dbPlant = this.plants.find(p => p.id === plant.id);
        const condition = dbPlant ? (dbPlant.condition || { color: '#22c55e', icon: 'spa' }) : { color: '#22c55e', icon: 'spa' };

        const isContainer = (plant.planting_type || 'container') === 'container';
        let baseHeight = 0;

        if (isContainer) {
          const potGeo = new THREE.CylinderGeometry(14, 10, 20, 16);
          const potMat = new THREE.MeshStandardMaterial({ color: 0xc25e2e, roughness: 0.85 });
          const pot = new THREE.Mesh(potGeo, potMat);
          pot.position.y = 10;
          pot.castShadow = true;
          pot.receiveShadow = true;
          group.add(pot);

          const soilGeo = new THREE.CylinderGeometry(13.5, 13.5, 2, 16);
          const soilMat = new THREE.MeshStandardMaterial({ color: 0x3e2723, roughness: 0.95 });
          const soil = new THREE.Mesh(soilGeo, soilMat);
          soil.position.y = 19;
          group.add(soil);
          baseHeight = 20;
        } else {
          const moundGeo = new THREE.ConeGeometry(16, 6, 16);
          const moundMat = new THREE.MeshStandardMaterial({ color: 0x4e342e, roughness: 0.95 });
          const mound = new THREE.Mesh(moundGeo, moundMat);
          mound.position.y = 3;
          group.add(mound);
          baseHeight = 5;
        }

        const pType = plant.plant_type || 'herb';
        this.buildProceduralPlant3D(group, pType, baseHeight);

        // Halo ring
        const ringGeo = new THREE.RingGeometry(18, 22, 32);
        const ringColor = new THREE.Color(condition.color || '#22c55e');
        const ringMat = new THREE.MeshBasicMaterial({
          color: ringColor,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.85
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.5;
        group.add(ring);

        if (this.selectedPlantId === plant.id) {
          const selectRingGeo = new THREE.RingGeometry(24, 27, 32);
          const selectRingMat = new THREE.MeshBasicMaterial({ color: 0xffeb3b, side: THREE.DoubleSide });
          const selectRing = new THREE.Mesh(selectRingGeo, selectRingMat);
          selectRing.rotation.x = -Math.PI / 2;
          selectRing.position.y = 0.8;
          group.add(selectRing);
        }

        group.userData = { type: 'plant', plantId: plant.id };
        this.threeScene.add(group);
        this.threePlantMeshes[plant.id] = group;
      });
    }

    buildProceduralPlant3D(group, type, baseHeight) {
      if (type === 'herb') {
        const leafMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.7 });
        for (let i = 0; i < 7; i++) {
          const angle = (i * Math.PI * 2) / 7;
          const leafGeo = new THREE.SphereGeometry(6, 8, 8);
          leafGeo.scale(0.8, 1.4, 0.4);
          const leaf = new THREE.Mesh(leafGeo, leafMat);
          leaf.position.set(Math.cos(angle) * 7, baseHeight + 10, Math.sin(angle) * 7);
          leaf.rotation.x = 0.3;
          leaf.rotation.y = angle;
          leaf.castShadow = true;
          group.add(leaf);
        }
      } else if (type === 'flower') {
        const stemGeo = new THREE.CylinderGeometry(1.5, 2, 18, 8);
        const stemMat = new THREE.MeshStandardMaterial({ color: 0x16a34a });
        const stem = new THREE.Mesh(stemGeo, stemMat);
        stem.position.y = baseHeight + 9;
        stem.castShadow = true;
        group.add(stem);

        const petalGeo = new THREE.SphereGeometry(9, 12, 12);
        const petalMat = new THREE.MeshStandardMaterial({ color: 0xd946ef, roughness: 0.6 });
        const blossom = new THREE.Mesh(petalGeo, petalMat);
        blossom.position.y = baseHeight + 20;
        blossom.castShadow = true;
        group.add(blossom);

        const centerGeo = new THREE.SphereGeometry(4, 8, 8);
        const centerMat = new THREE.MeshStandardMaterial({ color: 0xfacc15 });
        const center = new THREE.Mesh(centerGeo, centerMat);
        center.position.y = baseHeight + 22;
        group.add(center);
      } else if (type === 'shrub') {
        const shrubMat = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.85 });
        const offsets = [
          [0, 14, 0, 11], [-6, 12, -4, 8], [6, 12, 4, 8], [4, 11, -5, 8], [-5, 11, 5, 8]
        ];
        offsets.forEach(([ox, oy, oz, r]) => {
          const sphGeo = new THREE.SphereGeometry(r, 10, 10);
          const sph = new THREE.Mesh(sphGeo, shrubMat);
          sph.position.set(ox, baseHeight + oy, oz);
          sph.castShadow = true;
          group.add(sph);
        });

        const berryMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8 });
        [[-4, 18, 3], [5, 16, -3], [2, 21, 1]].forEach(([bx, by, bz]) => {
          const bGeo = new THREE.SphereGeometry(2, 6, 6);
          const b = new THREE.Mesh(bGeo, berryMat);
          b.position.set(bx, baseHeight + by, bz);
          group.add(b);
        });
      } else if (type === 'vegetable') {
        const stakeGeo = new THREE.CylinderGeometry(1, 1, 30, 6);
        const stakeMat = new THREE.MeshStandardMaterial({ color: 0x854d0e });
        const stake = new THREE.Mesh(stakeGeo, stakeMat);
        stake.position.y = baseHeight + 15;
        group.add(stake);

        const leafMat = new THREE.MeshStandardMaterial({ color: 0x22c55e });
        for (let j = 0; j < 5; j++) {
          const lGeo = new THREE.SphereGeometry(6, 8, 8);
          lGeo.scale(1.3, 0.4, 1);
          const l = new THREE.Mesh(lGeo, leafMat);
          l.position.set((j % 2 === 0 ? 5 : -5), baseHeight + 8 + j * 4, 0);
          group.add(l);
        }

        const tomatoMat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.4 });
        [[-4, baseHeight + 12, 3], [4, baseHeight + 16, -2]].forEach(([tx, ty, tz]) => {
          const tGeo = new THREE.SphereGeometry(4, 10, 10);
          const t = new THREE.Mesh(tGeo, tomatoMat);
          t.position.set(tx, ty, tz);
          t.castShadow = true;
          group.add(t);
        });
      } else if (type === 'tree') {
        const trunkGeo = new THREE.CylinderGeometry(3, 4.5, 24, 8);
        const trunkMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.9 });
        const trunk = new THREE.Mesh(trunkGeo, trunkMat);
        trunk.position.y = baseHeight + 12;
        trunk.castShadow = true;
        group.add(trunk);

        const canopyMat = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.8 });
        const canopy1 = new THREE.Mesh(new THREE.ConeGeometry(18, 22, 10), canopyMat);
        canopy1.position.y = baseHeight + 28;
        canopy1.castShadow = true;
        group.add(canopy1);

        const canopy2 = new THREE.Mesh(new THREE.ConeGeometry(14, 18, 10), canopyMat);
        canopy2.position.y = baseHeight + 38;
        canopy2.castShadow = true;
        group.add(canopy2);
      }
    }

    handleThreeClick(e) {
      if (!this.threeRaycaster || !this.threeCamera || !this.threeContainer) return;

      const rect = this.threeContainer.getBoundingClientRect();
      this.threeMouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.threeMouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.threeRaycaster.setFromCamera(this.threeMouse, this.threeCamera);
      const intersects = this.threeRaycaster.intersectObjects(this.threeScene.children, true);

      for (let hit of intersects) {
        let cur = hit.object;
        while (cur && cur !== this.threeScene) {
          if (cur.userData && cur.userData.type === 'plant') {
            this.selectPlant(cur.userData.plantId);
            return;
          } else if (cur.userData && cur.userData.type === 'area') {
            this.selectArea(cur.userData.areaId);
            return;
          }
          cur = cur.parent;
        }
      }
    }

    fitToGarden() {
      if (this.activeDimension === '2d') {
        if (this.layout.areas.length === 0) {
          this.panX = 50;
          this.panY = 50;
          this.zoom = 1.0;
        } else {
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          this.layout.areas.forEach(a => {
            const b = Geometry.polygonBounds(a.points);
            minX = Math.min(minX, b.minX);
            minY = Math.min(minY, b.minY);
            maxX = Math.max(maxX, b.maxX);
            maxY = Math.max(maxY, b.maxY);
          });
          const cw = this.canvas.width / (window.devicePixelRatio || 1);
          const ch = this.canvas.height / (window.devicePixelRatio || 1);
          const gw = maxX - minX + 100;
          const gh = maxY - minY + 100;

          this.zoom = Math.min(1.8, Math.max(0.4, Math.min(cw / gw, ch / gh)));
          this.panX = (cw - gw * this.zoom) / 2 - minX * this.zoom + 50;
          this.panY = (ch - gh * this.zoom) / 2 - minY * this.zoom + 50;
        }
        this.renderCanvas2D();
      } else if (this.threeControls && this.threeCamera) {
        let cx = 200, cz = 150;
        if (this.layout.areas.length > 0) {
          let sumX = 0, sumZ = 0;
          this.layout.areas.forEach(a => {
            const c = Geometry.polygonCentroid(a.points);
            sumX += c.x;
            sumZ += c.y;
          });
          cx = sumX / this.layout.areas.length;
          cz = sumZ / this.layout.areas.length;
        }
        this.threeControls.target.set(cx, 0, cz);
        this.threeCamera.position.set(cx + 350, 400, cz + 350);
        this.threeControls.update();
      }
    }

    rotate3D(deltaAngleDegrees) {
      if (!this.threeControls || !this.threeCamera) return;
      const angleRad = (deltaAngleDegrees * Math.PI) / 180;
      const pos = this.threeCamera.position;
      const target = this.threeControls.target;

      const dx = pos.x - target.x;
      const dz = pos.z - target.z;
      const curAngle = Math.atan2(dz, dx);
      const dist = Math.sqrt(dx * dx + dz * dz);

      const newAngle = curAngle + angleRad;
      pos.x = target.x + dist * Math.cos(newAngle);
      pos.z = target.z + dist * Math.sin(newAngle);
      this.threeControls.update();
    }

    // --- Side Panel Details & Quick Actions ---
    renderSidePanel() {
      const panel = document.getElementById('garden-side-panel');
      if (!panel) return;

      if (!this.selectedPlantId && !this.selectedAreaId) {
        panel.classList.remove('open');
        return;
      }

      panel.classList.add('open');

      if (this.selectedPlantId) {
        this.renderPlantSidePanel(panel);
      } else if (this.selectedAreaId) {
        this.renderAreaSidePanel(panel);
      }
    }

    renderPlantSidePanel(panel) {
      const plant = this.plants.find(p => p.id === this.selectedPlantId);
      const layoutPlant = this.layout.plants.find(p => p.id === this.selectedPlantId);
      if (!plant) return;

      const condition = plant.condition || {
        status_code: 'doing_well',
        badge_label: 'Doing well',
        color: '#22c55e',
        icon: 'spa',
        primary_reason: 'Plant is healthy and thriving.',
        secondary_concerns: [],
        recommended_action: 'Continue regular monitoring and routine care.'
      };

      const dbArea = this.growingAreas.find(a => a.id === plant.area_id);
      const isSheltered = dbArea ? dbArea.shelter_from_rain : false;
      const latestObs = condition.latest_observation;

      let obsHtml = `<div class="side-sub-note">No recent journal observations recorded.</div>`;
      if (latestObs) {
        obsHtml = `
          <div class="side-obs-card">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-bottom:0.2rem;">
              <span>CATEGORY: <strong>${(latestObs.category || 'general').toUpperCase()}</strong></span>
              <span>${new Date(latestObs.timestamp).toLocaleDateString()}</span>
            </div>
            <div style="font-size:0.86rem; line-height:1.4;">${latestObs.notes}</div>
            ${latestObs.photo_url ? `<img src="${latestObs.photo_url}" style="width:100%; border-radius:6px; margin-top:0.4rem; max-height:140px; object-fit:cover;">` : ''}
          </div>
        `;
      }

      panel.innerHTML = `
        <div class="side-panel-header">
          <div>
            <div class="side-title">${plant.name}</div>
            <div class="side-sub"><em>${plant.species || 'Species unassigned'}</em></div>
          </div>
          <button class="side-close-btn" onclick="window.gardenPlanner.clearSelection()">✕</button>
        </div>

        <div class="side-section">
          <div class="side-condition-card" style="border-left: 4px solid ${condition.color};">
            <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.3rem;">
              <span class="material-symbols-outlined" style="color:${condition.color}; font-size:1.3rem;">${condition.icon}</span>
              <strong style="color:${condition.color}; font-size:0.95rem;">${condition.badge_label}</strong>
            </div>
            <div style="font-size:0.86rem; color:var(--text); line-height:1.4;">
              ${condition.primary_reason}
            </div>
            ${condition.secondary_concerns && condition.secondary_concerns.length > 0 ? `
              <div style="margin-top:0.4rem; font-size:0.78rem; color:var(--text-muted);">
                <strong>Also noted:</strong> ${condition.secondary_concerns.join('; ')}
              </div>
            ` : ''}
          </div>
        </div>

        <div class="side-section">
          <div class="side-label">RECOMMENDED NEXT ACTION</div>
          <div class="side-action-box">
            <span class="material-symbols-outlined" style="font-size:1.1rem; color:var(--accent);">checklist</span>
            <div>${condition.recommended_action}</div>
          </div>
        </div>

        <div class="side-section">
          <div class="side-label">ENVIRONMENT & GROWING AREA</div>
          <div class="side-meta-row">
            <span>Area:</span>
            <select id="side-select-area" onchange="window.gardenPlanner.handleAreaSelectChange('${plant.id}', this.value)" style="padding:0.3rem 0.5rem; border-radius:4px; border:1px solid var(--border); font-size:0.82rem;">
              ${this.growingAreas.map(a => `<option value="${a.id}" ${a.id === plant.area_id ? 'selected' : ''}>${a.name} (${a.area_type})</option>`).join('')}
            </select>
          </div>
          <div class="side-meta-row">
            <span>Micro-climate:</span>
            <span class="pill ${isSheltered ? 'sheltered' : 'open'}">${isSheltered ? 'Sheltered (Zero Rain)' : 'Open Exposure'}</span>
          </div>
          <div class="side-meta-row">
            <span>Planting Type:</span>
            <span>${plant.planting_type || 'container'} ${plant.container_size_liters ? '(' + plant.container_size_liters + 'L)' : ''}</span>
          </div>
        </div>

        ${layoutPlant ? `
          <div class="side-section">
            <div class="side-label">VISUAL SIZE & ORIENTATION</div>
            <div style="display:flex; gap:0.8rem; align-items:center; margin-bottom:0.4rem;">
              <span style="font-size:0.78rem; width:45px;">Scale:</span>
              <input type="range" min="0.6" max="2.0" step="0.1" value="${layoutPlant.scale || 1.0}" oninput="window.gardenPlanner.updatePlantScale('${plant.id}', this.value)" style="flex:1;">
              <span style="font-size:0.78rem; width:30px;">${(layoutPlant.scale || 1.0).toFixed(1)}x</span>
            </div>
            <div style="display:flex; gap:0.8rem; align-items:center;">
              <span style="font-size:0.78rem; width:45px;">Rotate:</span>
              <input type="range" min="0" max="360" step="15" value="${layoutPlant.rotation || 0}" oninput="window.gardenPlanner.updatePlantRotation('${plant.id}', this.value)" style="flex:1;">
              <span style="font-size:0.78rem; width:30px;">${layoutPlant.rotation || 0}°</span>
            </div>
          </div>
        ` : ''}

        <div class="side-section">
          <div class="side-label">LATEST JOURNAL OBSERVATION</div>
          ${obsHtml}
        </div>

        <div class="side-section">
          <div class="side-label">QUICK CARE ACTIONS</div>
          <div style="display:flex; flex-direction:column; gap:0.5rem; margin-top:0.4rem;">
            <button class="btn btn-action" onclick="window.gardenPlanner.quickWaterPlant('${plant.id}')">
              <span class="material-symbols-outlined">water_drop</span> Record Watering
            </button>

            <div style="display:flex; gap:0.4rem;">
              <input id="side-quick-obs-text" placeholder="Add observation note..." style="flex:1; padding:0.4rem 0.6rem; border:1px solid var(--border); border-radius:6px; font-size:0.82rem;">
              <select id="side-quick-obs-cat" style="padding:0.4rem; border:1px solid var(--border); border-radius:6px; font-size:0.8rem;">
                <option value="watering">Watering</option>
                <option value="symptom">Symptom</option>
                <option value="pruning">Pruning</option>
                <option value="general">General</option>
              </select>
              <button class="btn" style="padding:0.4rem 0.8rem; font-size:0.8rem;" onclick="window.gardenPlanner.quickAddObservation('${plant.id}')">Log</button>
            </div>

            <div style="display:flex; gap:0.4rem; margin-top:0.4rem;">
              <button class="btn btn-outline" style="flex:1; font-size:0.8rem;" onclick="window.gardenPlanner.promptAttachPhoto('${plant.id}')">
                <span class="material-symbols-outlined" style="font-size:1rem; vertical-align:middle;">add_a_photo</span> Add Photo
              </button>
              <button class="btn btn-outline" style="flex:1; font-size:0.8rem;" onclick="window.gardenPlanner.unplacePlant('${plant.id}')">
                <span class="material-symbols-outlined" style="font-size:1rem; vertical-align:middle;">backspace</span> Unplace
              </button>
            </div>

            <button class="btn btn-danger-outline" style="margin-top:0.4rem; font-size:0.78rem;" onclick="window.gardenPlanner.deletePlant('${plant.id}')">
              Delete Plant Permanently
            </button>
          </div>
        </div>
      `;
    }

    renderAreaSidePanel(panel) {
      const area = this.growingAreas.find(a => a.id === this.selectedAreaId);
      if (!area) return;

      const areaPlants = this.plants.filter(p => p.area_id === area.id);

      panel.innerHTML = `
        <div class="side-panel-header">
          <div>
            <div class="side-title">${area.name}</div>
            <div class="side-sub">${area.area_type.toUpperCase()} GROWING AREA</div>
          </div>
          <button class="side-close-btn" onclick="window.gardenPlanner.clearSelection()">✕</button>
        </div>

        <div class="side-section">
          <div class="side-label">ENVIRONMENTAL CONDITIONS</div>
          <div class="side-meta-row">
            <span>Sun Exposure:</span>
            <span style="font-weight:600;">${area.sun_exposure}</span>
          </div>
          <div class="side-meta-row">
            <span>Shelter from Rain:</span>
            <span class="pill ${area.shelter_from_rain ? 'sheltered' : 'open'}">
              ${area.shelter_from_rain ? 'Sheltered (Zero Direct Rain)' : 'Open Exposure'}
            </span>
          </div>
          <div class="side-meta-row">
            <span>Watering Arrangements:</span>
            <span>${area.watering_arrangements || 'Manual watering'}</span>
          </div>
        </div>

        <div class="side-section">
          <div class="side-label">PLANTS IN THIS AREA (${areaPlants.length})</div>
          <div style="display:flex; flex-direction:column; gap:0.4rem; margin-top:0.4rem;">
            ${areaPlants.map(p => `
              <div class="lib-plant-card" style="padding:0.4rem 0.6rem; cursor:pointer;" onclick="window.gardenPlanner.selectPlant('${p.id}')">
                <span style="font-size:1.1rem;">${this.getPlantTypeEmoji(this.inferPlantType(p.name, p.species))}</span>
                <span style="font-weight:600; font-size:0.86rem; flex:1;">${p.name}</span>
                <span class="material-symbols-outlined" style="font-size:1rem; color:${p.condition ? p.condition.color : '#22c55e'};">${p.condition ? p.condition.icon : 'spa'}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="side-section" style="margin-top:1.5rem;">
          <button class="btn btn-danger-outline" style="width:100%; font-size:0.8rem;" onclick="window.gardenPlanner.deleteArea('${area.id}')">
            Delete Growing Area
          </button>
        </div>
      `;
    }

    updatePlantScale(plantId, newScale) {
      const lp = this.layout.plants.find(p => p.id === plantId);
      if (lp) {
        lp.scale = parseFloat(newScale);
        if (this.activeDimension === '2d') this.renderCanvas2D();
        else this.renderThree3D();
        this.scheduleSave();
      }
    }

    updatePlantRotation(plantId, newRotation) {
      const lp = this.layout.plants.find(p => p.id === plantId);
      if (lp) {
        lp.rotation = parseInt(newRotation, 10);
        if (this.activeDimension === '2d') this.renderCanvas2D();
        else this.renderThree3D();
        this.scheduleSave();
      }
    }

    async handleAreaSelectChange(plantId, newAreaId) {
      this.pushUndo();
      await this.reassignPlantArea(plantId, newAreaId);
      const lp = this.layout.plants.find(p => p.id === plantId);
      if (lp) lp.area_id = newAreaId;
      this.scheduleSave();
      this.renderAll();
      this.showToast(`Updated plant area to ${this.getAreaName(newAreaId)}.`);
    }

    async quickWaterPlant(plantId) {
      try {
        const res = await fetch(`/api/plants/${plantId}/quick-care`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'water', notes: 'Watered thoroughly until slight drainage occurred.' })
        });
        const data = await res.json();
        if (data.status === 'success') {
          const p = this.plants.find(dp => dp.id === plantId);
          if (p && data.condition) {
            p.condition = data.condition;
          }
          this.renderAll();
          this.showToast("Watering recorded! Care status refreshed to Doing well.");
        }
      } catch (err) {
        console.error("Quick water failed:", err);
      }
    }

    async quickAddObservation(plantId) {
      const textInput = document.getElementById('side-quick-obs-text');
      const catSelect = document.getElementById('side-quick-obs-cat');
      const notes = textInput ? textInput.value.trim() : '';
      const category = catSelect ? catSelect.value : 'general';

      if (!notes) return;

      try {
        const res = await fetch(`/api/plants/${plantId}/quick-care`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'observe', notes: notes, category: category })
        });
        const data = await res.json();
        if (data.status === 'success') {
          const p = this.plants.find(dp => dp.id === plantId);
          if (p && data.condition) {
            p.condition = data.condition;
          }
          if (textInput) textInput.value = '';
          this.renderAll();
          this.showToast("Observation logged! Care recommendations updated.");
        }
      } catch (err) {
        console.error("Observation failed:", err);
      }
    }

    async promptAttachPhoto(plantId) {
      const photoUrl = prompt("Enter a photo URL or sample image link for this plant:", "https://images.unsplash.com/photo-1592417817098-8f3d6eb226c7?w=500&auto=format&fit=crop&q=80");
      if (!photoUrl) return;

      try {
        const res = await fetch(`/api/plants/${plantId}/quick-care`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'photo', photo_url: photoUrl, notes: 'Photo uploaded.' })
        });
        const data = await res.json();
        if (data.status === 'success') {
          const p = this.plants.find(dp => dp.id === plantId);
          if (p && data.condition) {
            p.condition = data.condition;
          }
          this.renderAll();
          this.showToast("Photo attached to plant journal.");
        }
      } catch (err) {
        console.error("Photo attach failed:", err);
      }
    }

    unplacePlant(plantId) {
      this.pushUndo();
      this.layout.plants = this.layout.plants.filter(p => p.id !== plantId);
      this.clearSelection();
      this.scheduleSave();
      this.renderAll();
      this.showToast("Plant removed from canvas (available in Library under Awaiting Placement).");
    }

    async deletePlant(plantId) {
      if (!confirm("Are you sure you want to permanently delete this plant profile and care history?")) return;
      this.pushUndo();
      try {
        await fetch(`/api/plants/${plantId}`, { method: 'DELETE' });
        this.plants = this.plants.filter(p => p.id !== plantId);
        this.layout.plants = this.layout.plants.filter(p => p.id !== plantId);
        this.clearSelection();
        this.scheduleSave();
        this.renderAll();
        this.showToast("Plant deleted.");
      } catch (err) {
        console.error("Delete plant failed:", err);
      }
    }

    async deleteArea(areaId) {
      if (!confirm("Are you sure you want to delete this growing area? Plants in this area will need to be reassigned.")) return;
      this.pushUndo();
      try {
        await fetch(`/api/areas/${areaId}`, { method: 'DELETE' });
        this.growingAreas = this.growingAreas.filter(a => a.id !== areaId);
        this.layout.areas = this.layout.areas.filter(a => a.id !== areaId);
        this.clearSelection();
        this.scheduleSave();
        this.renderAll();
        this.showToast("Growing area deleted.");
      } catch (err) {
        console.error("Delete area failed:", err);
      }
    }

    // --- View Modes: Visual vs List & 2D vs 3D ---
    setViewMode(mode) {
      this.currentViewMode = mode;
      const visualWorkspace = document.getElementById('garden-visual-workspace');
      const listView = document.getElementById('garden-list-view');
      const btnVisual = document.getElementById('btn-mode-visual');
      const btnList = document.getElementById('btn-mode-list');

      if (mode === 'visual') {
        if (visualWorkspace) visualWorkspace.style.display = 'flex';
        if (listView) listView.style.display = 'none';
        if (btnVisual) btnVisual.classList.add('active');
        if (btnList) btnList.classList.remove('active');
        this.renderAll();
      } else {
        if (visualWorkspace) visualWorkspace.style.display = 'none';
        if (listView) listView.style.display = 'block';
        if (btnVisual) btnVisual.classList.remove('active');
        if (btnList) btnList.classList.add('active');
        this.renderListView();
      }
    }

    setDimension(dim) {
      this.activeDimension = dim;
      const canvas2D = document.getElementById('garden-canvas-2d');
      const container3D = document.getElementById('garden-canvas-3d-container');
      const btn2D = document.getElementById('btn-dim-2d');
      const btn3D = document.getElementById('btn-dim-3d');
      const toolbar2DOnly = document.querySelectorAll('.tool-2d-only');

      if (dim === '2d') {
        if (canvas2D) canvas2D.style.display = 'block';
        if (container3D) container3D.style.display = 'none';
        if (btn2D) btn2D.classList.add('active');
        if (btn3D) btn3D.classList.remove('active');
        toolbar2DOnly.forEach(el => el.style.display = 'inline-flex');
        this.renderCanvas2D();
      } else {
        if (canvas2D) canvas2D.style.display = 'none';
        if (container3D) container3D.style.display = 'block';
        if (btn2D) btn2D.classList.remove('active');
        if (btn3D) btn3D.classList.add('active');
        toolbar2DOnly.forEach(el => el.style.display = 'none');
        this.renderThree3D();
      }
    }

    setMode(mode) {
      this.activeMode = mode;
      const btnExplore = document.getElementById('btn-mode-explore');
      const btnEdit = document.getElementById('btn-mode-edit');

      if (mode === 'explore') {
        if (btnExplore) btnExplore.classList.add('active');
        if (btnEdit) btnEdit.classList.remove('active');
        this.setTool('select');
      } else {
        if (btnExplore) btnExplore.classList.remove('active');
        if (btnEdit) btnEdit.classList.add('active');
      }
      this.renderCanvas2D();
    }

    setTool(tool) {
      this.activeTool = tool;
      document.querySelectorAll('.btn-tool').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById(`btn-tool-${tool}`);
      if (activeBtn) activeBtn.classList.add('active');

      if (tool !== 'select') {
        this.clearSelection();
      }
      this.renderCanvas2D();
    }

    // --- List View Synchronization ---
    renderListView() {
      const areasDiv = document.getElementById('garden-areas');
      const plantsDiv = document.getElementById('plants-list');
      if (!areasDiv || !plantsDiv) return;

      const filteredPlants = this.plants.filter(p => {
        const matchesCondition = this.filterCondition === 'all' || (p.condition && p.condition.status_code === this.filterCondition);
        const matchesArea = this.filterAreaId === 'all' || p.area_id === this.filterAreaId;
        return matchesCondition && matchesArea;
      });

      areasDiv.innerHTML = `
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.2rem;">
          ${this.growingAreas.map(a => `
            <div style="background:#fff; border:1px solid var(--border); border-radius:8px; padding:0.6rem 0.9rem; font-size:0.85rem; cursor:pointer;" onclick="window.gardenPlanner.setViewMode('visual'); window.gardenPlanner.selectArea('${a.id}');">
              <strong>${a.name}</strong> (${a.area_type})
              <div style="margin-top:0.2rem;">
                <span class="pill ${a.shelter_from_rain ? 'sheltered' : 'open'}">
                  ${a.shelter_from_rain ? 'Sheltered (Zero Rain)' : 'Open Exposure'}
                </span>
                <span style="color:var(--text-muted); margin-left:0.3rem;">${a.sun_exposure}</span>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      plantsDiv.innerHTML = filteredPlants.map(p => {
        const condition = p.condition || { color: '#22c55e', icon: 'spa', badge_label: 'Doing well', primary_reason: 'Healthy' };
        return `
          <div class="card" style="border-left: 4px solid ${condition.color};">
            <div class="card-header">
              <div>
                <div class="card-title">${p.name}</div>
                <div class="card-sub"><em>${p.species || 'Species unassigned'}</em></div>
              </div>
              <span class="pill" style="background:${condition.color}15; color:${condition.color}; font-weight:600;">
                <span class="material-symbols-outlined status-mini-icon">${condition.icon}</span> ${condition.badge_label}
              </span>
            </div>
            <div style="font-size:0.85rem; line-height:1.5; color:var(--text-muted); margin-top:0.4rem;">
              <div>Area: <strong>${p.area_name || 'Garden'}</strong> · Type: ${p.planting_type || 'container'} ${p.container_size_liters ? '(' + p.container_size_liters + 'L)' : ''}</div>
              <div style="color:var(--text); margin-top:0.3rem;"><strong>Condition reason:</strong> ${condition.primary_reason}</div>
            </div>
            <div style="display:flex; gap:0.4rem; margin-top:0.8rem;">
              <button class="btn btn-outline" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick="window.gardenPlanner.quickWaterPlant('${p.id}')">💧 Water</button>
              <button class="btn btn-outline" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick="window.gardenPlanner.setViewMode('visual'); window.gardenPlanner.selectPlant('${p.id}');">Visual Twin</button>
            </div>
          </div>
        `;
      }).join('');
    }

    showToast(message) {
      let toast = document.getElementById('garden-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'garden-toast';
        toast.className = 'garden-toast';
        document.body.appendChild(toast);
      }
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3000);
    }

    bindEvents() {
      const bind = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', fn);
      };

      bind('btn-mode-visual', () => this.setViewMode('visual'));
      bind('btn-mode-list', () => this.setViewMode('list'));
      bind('btn-dim-2d', () => this.setDimension('2d'));
      bind('btn-dim-3d', () => this.setDimension('3d'));
      bind('btn-mode-explore', () => this.setMode('explore'));
      bind('btn-mode-edit', () => this.setMode('edit'));

      bind('btn-tool-select', () => this.setTool('select'));
      bind('btn-tool-freehand', () => this.setTool('freehand'));
      bind('btn-tool-rect', () => this.setTool('rect'));
      bind('btn-tool-polygon', () => this.setTool('polygon'));

      bind('btn-tool-undo', () => this.undo());
      bind('btn-tool-redo', () => this.redo());

      bind('btn-zoom-in', () => {
        this.zoom = Math.min(3.0, this.zoom * 1.2);
        this.renderCanvas2D();
      });
      bind('btn-zoom-out', () => {
        this.zoom = Math.max(0.3, this.zoom / 1.2);
        this.renderCanvas2D();
      });
      bind('btn-fit-garden', () => this.fitToGarden());

      bind('btn-rotate-left', () => this.rotate3D(-45));
      bind('btn-rotate-right', () => this.rotate3D(45));

      bind('btn-add-area-dialog', () => {
        const defaultShape = [
          { x: 100, y: 100 }, { x: 380, y: 100 },
          { x: 380, y: 320 }, { x: 100, y: 320 }
        ];
        this.openAreaModalWithPoints(defaultShape, 'rectangle');
      });

      bind('btn-toggle-library', () => {
        const lib = document.getElementById('garden-library-drawer');
        if (lib) lib.classList.toggle('collapsed');
      });

      const areaSelect = document.getElementById('filter-area-select');
      if (areaSelect) {
        areaSelect.addEventListener('change', (e) => this.setAreaFilter(e.target.value));
      }
    }
  }

  window.gardenPlanner = new GardenPlanner();

})(window);
