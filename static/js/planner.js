        // SAVED_ROUTES_KEY removed
        let savedRoutes = [];
        let savedRoutesCount = 0;
        let latestPlanResponse = null;

        // Map State
        let transitMap = null;
        let routeLayerGroup = null;
        let markerLayerGroup = null;

        function initMap() {
            const mapContainer = document.getElementById('route-map');
            if (!mapContainer) return;
            
            try {
                transitMap = L.map('route-map', {
                    zoomControl: false
                }).setView([23.750, 90.390], 12);
                
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(transitMap);
                
                L.control.zoom({
                    position: 'bottomright'
                }).addTo(transitMap);
                
                routeLayerGroup = L.layerGroup().addTo(transitMap);
                markerLayerGroup = L.layerGroup().addTo(transitMap);
            } catch (err) {
                console.error("Map initialization failed", err);
            }
        }

        function drawRouteMap(mapData) {
            if (!transitMap) return;
            
            const placeholder = document.getElementById('map-placeholder');
            if (!mapData || !mapData.legs || mapData.legs.length === 0) {
                if (placeholder) placeholder.classList.remove('d-none');
                routeLayerGroup.clearLayers();
                markerLayerGroup.clearLayers();
                return;
            }
            
            if (placeholder) placeholder.classList.add('d-none');
            
            routeLayerGroup.clearLayers();
            markerLayerGroup.clearLayers();
            
            const bounds = L.latLngBounds();
            
            if (mapData.origin) {
                const oLat = mapData.origin.lat;
                const oLon = mapData.origin.lon;
                const marker = L.marker([oLat, oLon]).bindPopup(`<b>Origin</b><br>${mapData.origin.name}`);
                markerLayerGroup.addLayer(marker);
                bounds.extend([oLat, oLon]);
            }
            
            if (mapData.destination) {
                const dLat = mapData.destination.lat;
                const dLon = mapData.destination.lon;
                const marker = L.marker([dLat, dLon]).bindPopup(`<b>Destination</b><br>${mapData.destination.name}`);
                markerLayerGroup.addLayer(marker);
                bounds.extend([dLat, dLon]);
            }
            
            mapData.legs.forEach(leg => {
                if (leg.frm && leg.to) {
                    const path = [
                        [leg.frm.lat, leg.frm.lon],
                        [leg.to.lat, leg.to.lon]
                    ];
                    bounds.extend(path[0]);
                    bounds.extend(path[1]);
                    
                    let color = '#0D6EFD';
                    let dashArray = '5, 5';
                    let weight = 4;
                    
                    if (leg.mode === 'metro' || leg.mode === 'train') {
                        color = '#DC3545';
                        dashArray = null;
                        weight = 5;
                    } else if (leg.mode === 'bus') {
                        color = '#198754';
                        dashArray = null;
                        weight = 5;
                    }
                    
                    const polyline = L.polyline(path, {
                        color: color,
                        weight: weight,
                        dashArray: dashArray,
                        opacity: 0.8
                    });
                    
                    if (leg.frm.id !== '__USER_ORIGIN__' && leg.frm.id !== '__USER_DESTINATION__') {
                        const circle = L.circleMarker([leg.frm.lat, leg.frm.lon], {
                            radius: 4,
                            fillColor: '#ffffff',
                            color: color,
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 1
                        }).bindPopup(`<b>${leg.frm.name}</b><br>Mode: ${leg.mode}`);
                        markerLayerGroup.addLayer(circle);
                    }
                    
                    routeLayerGroup.addLayer(polyline);
                }
            });
            
            if (bounds.isValid()) {
                transitMap.fitBounds(bounds, { padding: [30, 30] });
            }
        }

        let currentSelectedRouteIndex = -1;

        function selectRouteCard(index) {
            currentSelectedRouteIndex = index;
            document.querySelectorAll('.route-card-item').forEach(el => {
                if (el.style.border.includes('2px solid rgb(0, 0, 0)') || el.style.border.includes('2px solid #000')) {
                    el.style.border = '2px solid #E5E7EB';
                } else {
                    el.style.border = '2px solid #E5E7EB';
                }
            });
            const activeCard = document.getElementById(`route-card-${index}`);
            if (activeCard) {
                activeCard.style.border = '2px solid #000';
            }
            
            if (latestPlanResponse && latestPlanResponse.data && latestPlanResponse.data.recommendations) {
                const rec = latestPlanResponse.data.recommendations[index];
                if (rec && rec.map) {
                    drawRouteMap(rec.map);
                } else {
                    drawRouteMap(null);
                }
            }
        }

        function loadSavedRoutes() {
            const container = document.getElementById('saved-cards-list');
            if (container && savedRoutes.length === 0) {
                container.innerHTML = '<div class="text-center mt-3"><span class="spinner-border spinner-border-sm text-secondary" role="status"></span> <span class="ms-2 text-muted" style="font-size:14px;">Loading saved routes...</span></div>';
            }
            fetch('/api/saved-routes')
                .then(res => res.json())
                .then(resData => {
                    if (resData.success && resData.data) {
                        savedRoutes = resData.data.map(dbRow => {
                            return {
                                id: dbRow.id,
                                origin: dbRow.origin,
                                destination: dbRow.destination,
                                route_data: dbRow.route_data || {},
                                created_at: dbRow.created_at
                            };
                        });
                    } else {
                        savedRoutes = [];
                    }
                    savedRoutesCount = savedRoutes.length;
                    updateSavedBadge();
                    renderSavedRoutesTab();
                    
                    // Trigger a re-render of the Plan tab save buttons if needed
                    const queryInput = document.getElementById('journey-query');
                    if (queryInput && latestPlanResponse) {
                        // The easiest way is to let the DOM be and the icons update when re-searched,
                        // but toggleSaveRoute handles the direct icon update.
                    }
                })
                .catch(err => {
                    console.error("Failed to load saved routes", err);
                    savedRoutes = [];
                    savedRoutesCount = 0;
                    updateSavedBadge();
                    renderSavedRoutesTab();
                });
        }

        // Show temporary toast notification
        function showToast(msg) {
            const toast = document.getElementById('global-toast');
            const label = document.getElementById('toast-message');
            if (!toast || !label) return;
            label.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2500);
        }

        // Switch between the 3 main bottom tabs
        function switchTab(tabId) {
            const tabs = ['tab-plan', 'tab-lines', 'tab-saved'];
            const navButtons = {
                'tab-plan': document.getElementById('nav-btn-plan'),
                'tab-lines': document.getElementById('nav-btn-lines'),
                'tab-saved': document.getElementById('nav-btn-saved')
            };

            tabs.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    if (id === tabId) {
                        el.classList.add('active-tab');
                        if (tabId === 'tab-plan' && transitMap) {
                            setTimeout(() => {
                                transitMap.invalidateSize();
                            }, 50);
                        }
                    } else {
                        el.classList.remove('active-tab');
                    }
                }
            });

            Object.keys(navButtons).forEach(id => {
                const btn = navButtons[id];
                if (btn) {
                    if (id === tabId) {
                        btn.classList.add('active');
                    } else {
                        btn.classList.remove('active');
                    }
                }
            });

            // Scroll smoothly to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            // If switching to saved tab, fetch routes
            if (tabId === 'tab-saved') {
                loadSavedRoutes();
            }
        }

        // Update Saved Counter across badge and headers
        function updateSavedBadge() {
            const badge = document.getElementById('nav-saved-badge');
            const headerBadge = document.getElementById('saved-header-counter');
            const emptyState = document.getElementById('saved-empty-state');
            const cardsList = document.getElementById('saved-cards-list');
            const navIcon = document.getElementById('nav-saved-icon');

            if (badge) {
                badge.textContent = savedRoutesCount;
                badge.style.display = savedRoutesCount > 0 ? 'flex' : 'none';
            }

            if (headerBadge) {
                headerBadge.textContent = savedRoutesCount === 1 ? '1 Saved Journey' : `${savedRoutesCount} Saved Journeys`;
            }

            if (navIcon) {
                if (savedRoutesCount > 0) {
                    navIcon.className = 'bi bi-bookmark-fill';
                } else {
                    navIcon.className = 'bi bi-bookmark';
                }
            }

            if (emptyState && cardsList) {
                if (savedRoutesCount === 0) {
                    emptyState.classList.remove('d-none');
                } else {
                    emptyState.classList.add('d-none');
                }
            }
        }

        // Toggle save route from Plan Trip tab
        function toggleSaveRoute(button, routeDataStr) {
            const payload = JSON.parse(decodeURIComponent(routeDataStr));
            const origin = payload.origin;
            const destination = payload.destination;
            const route_data = payload.route_data;
            const icon = button.querySelector('i');
            
            // Match exactly with what was stored
            const existingIdx = savedRoutes.findIndex(r => r.origin === origin && r.destination === destination && r.route_data && r.route_data.mode_sequence === route_data.mode_sequence && r.route_data.time_min === route_data.time_min);

            if (existingIdx >= 0) {
                // Unsave
                removeSavedRoute(savedRoutes[existingIdx].id);
                button.classList.remove('saved');
                if (icon) icon.className = 'bi bi-bookmark';
            } else {
                // Save
                button.disabled = true;
                const originalHtml = button.innerHTML;
                button.innerHTML = '<span class="spinner-border spinner-border-sm" style="width: 1rem; height: 1rem;" role="status"></span>';
                
                fetch('/api/saved-routes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ origin, destination, route_data })
                })
                .then(res => res.json())
                .then(data => {
                    button.disabled = false;
                    button.innerHTML = originalHtml;
                    if (data.success) {
                        if (data.already_saved) {
                            showToast('Already Saved');
                        } else {
                            showToast('Route saved to Saved tab!');
                        }
                        button.classList.add('saved');
                        if (icon) icon.className = 'bi bi-bookmark-fill';
                        loadSavedRoutes();
                    } else {
                        showToast('Failed to save route');
                    }
                })
                .catch(err => {
                    button.disabled = false;
                    button.innerHTML = originalHtml;
                    showToast('Failed to save route');
                });
            }
        }

        // Remove saved route directly from the Saved Tab
        function removeSavedRoute(routeKey) {
            const btn = document.getElementById(`btn-remove-${routeKey}`);
            let originalHtml = '';
            if (btn) {
                btn.disabled = true;
                originalHtml = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" style="width: 1rem; height: 1rem;" role="status"></span>';
            }

            fetch(`/api/saved-routes/${routeKey}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast('Route removed');
                    // Sync bookmark button on Plan tab if present
                    const planBtn = document.getElementById(`btn-save-${routeKey}`); // Only works if we assigned routeKey to planBtn
                    if (planBtn) {
                        planBtn.classList.remove('saved');
                        const icon = planBtn.querySelector('i');
                        if (icon) icon.className = 'bi bi-bookmark';
                    }
                    loadSavedRoutes();
                } else {
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                    }
                    showToast('Failed to remove route');
                }
            })
            .catch(err => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
                showToast('Failed to remove route');
            });
        }
        
        function renderSavedRoutesTab() {
            const container = document.getElementById('saved-cards-list');
            if (!container) return;
            
            if (savedRoutes.length === 0) {
                container.innerHTML = '';
                return;
            }
            
            let html = '';
            savedRoutes.forEach(r => {
                const rd = r.route_data || {};
                const costHtml = rd.cost_bdt != null ? '৳' + rd.cost_bdt : 'Cost N/A';
                const timeHtml = rd.time_min != null ? rd.time_min + ' min' : 'N/A';
                const transfersHtml = rd.transfers != null ? rd.transfers + ' transfer(s)' : 'N/A transfer(s)';
                const walkHtml = rd.walk_km != null ? 'Walk ' + rd.walk_km + ' km' : '';
                
                html += `
                <div class="uber-card p-3 mb-3 position-relative" id="saved-item-${r.id}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="fw-bold" style="font-size: 14px; color: #111111;">${r.origin} → ${r.destination}</div>
                        <button aria-label="Remove saved route" class="btn-bookmark-action saved" id="btn-remove-${r.id}" onclick="removeSavedRoute('${r.id}')" title="Remove" type="button">
                            <i class="bi bi-trash text-danger"></i>
                        </button>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="fw-bold" style="font-size: 16px; color: #111111;">${costHtml}</span>
                    </div>
                    <div class="d-flex flex-wrap gap-3 text-muted" style="font-size: 12.5px;">
                        <span><strong>${timeHtml}</strong></span>
                        <span><strong>${transfersHtml}</strong></span>
                        <span><strong>${walkHtml}</strong></span>
                    </div>
                    <div class="mt-2 text-muted" style="font-size: 12px;">
                        Modes: ${rd.mode_sequence || 'N/A'}
                    </div>
                </div>
                `;
            });
            container.innerHTML = html;
        }

        // Open route in planner
        function loadSavedRouteInPlanner(origin, dest) {
            const textarea = document.getElementById('journey-query');
            if (textarea) {
                textarea.value = `${origin} to ${dest}`;
            }
            switchTab('tab-plan');
            showToast(`Loaded ${origin} → ${dest} in planner`);
        }

        // Filter Transit lines
        function filterLines(category, btn) {
            const chips = document.querySelectorAll('#line-filters-wrap .line-filter-chip');
            chips.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');

            const items = document.querySelectorAll('#transit-lines-container .line-item-card');
            items.forEach(item => {
                const itemCat = item.getAttribute('data-category');
                if (category === 'all' || itemCat === category) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }

        // Toggle profile popover dropdown
        function toggleProfileDropdown(e) {
            if (e) e.stopPropagation();
            const menu = document.getElementById('profile-dropdown-menu');
            const btn = document.getElementById('profile-avatar-btn');
            if (!menu) return;

            const isClosed = menu.classList.contains('d-none');
            if (isClosed) {
                menu.classList.remove('d-none');
                if (btn) btn.setAttribute('aria-expanded', 'true');
            } else {
                menu.classList.add('d-none');
                if (btn) btn.setAttribute('aria-expanded', 'false');
            }
        }

        // Close dropdown on outside click
        document.addEventListener('click', function (e) {
            const container = document.getElementById('profile-dropdown-container');
            const menu = document.getElementById('profile-dropdown-menu');
            const btn = document.getElementById('profile-avatar-btn');
            if (container && !container.contains(e.target) && menu && !menu.classList.contains('d-none')) {
                menu.classList.add('d-none');
                if (btn) btn.setAttribute('aria-expanded', 'false');
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                const menu = document.getElementById('profile-dropdown-menu');
                const btn = document.getElementById('profile-avatar-btn');
                if (menu && !menu.classList.contains('d-none')) {
                    menu.classList.add('d-none');
                    if (btn) btn.setAttribute('aria-expanded', 'false');
                }
            }
        });

        // Handle profile view
        function viewProfile(e) {
            if (e) e.stopPropagation();
            const menu = document.getElementById('profile-dropdown-menu');
            if (menu) menu.classList.add('d-none');
            
            fetch('/api/auth/me')
                .then(res => res.json())
                .then(data => {
                    if (data.authenticated && data.user) {
                        showToast(`Logged in as ${data.user.full_name} (${data.user.email})`);
                    }
                })
                .catch(() => showToast('Profile details unavailable'));
        }

        // Handle logout action
        function handleLogout(e) {
            if (e) e.stopPropagation();
            const menu = document.getElementById('profile-dropdown-menu');
            if (menu) menu.classList.add('d-none');
            fetch('/api/auth/logout', { method: 'POST' })
                .then(() => { window.location.href = '/'; })
                .catch(() => { window.location.href = '/'; });
        }

        // Toggle collapsible drawer sections
        function toggleAccordion(contentId, iconId) {
            const content = document.getElementById(contentId);
            const icon = document.getElementById(iconId);
            if (!content) return;

            const isHidden = content.classList.contains('d-none');
            if (isHidden) {
                content.classList.remove('d-none');
                if (icon) {
                    icon.classList.remove('bi-chevron-down');
                    icon.classList.add('bi-chevron-up');
                }
            } else {
                content.classList.add('d-none');
                if (icon) {
                    icon.classList.remove('bi-chevron-up');
                    icon.classList.add('bi-chevron-down');
                }
            }
        }

        function toggleResultFilter(filterName) {
            if (!latestPlanResponse || !latestPlanResponse.data || !latestPlanResponse.data.recommendations) return;
            const recommendations = latestPlanResponse.data.recommendations;
            const buttons = document.querySelectorAll('#result-filter-container .pref-chip');
            
            let isActive = false;
            buttons.forEach(btn => {
                if (btn.getAttribute('data-filter') === filterName) {
                    if (btn.classList.contains('active')) {
                        btn.classList.remove('active');
                        isActive = false;
                    } else {
                        btn.classList.add('active');
                        isActive = true;
                    }
                } else {
                    btn.classList.remove('active');
                }
            });

            const countText = document.getElementById('recommendations-count-text');

            if (!isActive) {
                document.querySelectorAll('.route-card-item').forEach(el => el.classList.remove('d-none'));
                if (countText) countText.innerHTML = `· ${recommendations.length} recommendations found`;
                return;
            }

            let minVal = Infinity;
            recommendations.forEach(r => {
                let val = Infinity;
                if (filterName === 'Fastest' && r.time_min != null) val = r.time_min;
                else if (filterName === 'Lowest Cost' && r.cost_bdt != null) val = r.cost_bdt;
                else if (filterName === 'Less Walking' && r.walk_km != null) val = r.walk_km;
                else if (filterName === 'Fewer Transfers' && r.transfers != null) val = r.transfers;
                
                if (val < minVal) minVal = val;
            });

            let visibleCount = 0;
            let firstVisibleIdx = -1;
            let currentSelectedIsVisible = false;

            recommendations.forEach((r, idx) => {
                let val = Infinity;
                if (filterName === 'Fastest' && r.time_min != null) val = r.time_min;
                else if (filterName === 'Lowest Cost' && r.cost_bdt != null) val = r.cost_bdt;
                else if (filterName === 'Less Walking' && r.walk_km != null) val = r.walk_km;
                else if (filterName === 'Fewer Transfers' && r.transfers != null) val = r.transfers;
                
                const card = document.getElementById(`route-card-${idx}`);
                if (card) {
                    if (val === minVal && minVal !== Infinity) {
                        card.classList.remove('d-none');
                        visibleCount++;
                        if (firstVisibleIdx === -1) firstVisibleIdx = idx;
                        if (currentSelectedRouteIndex === idx) {
                            currentSelectedIsVisible = true;
                        }
                    } else {
                        card.classList.add('d-none');
                    }
                }
            });

            if (countText) countText.innerHTML = `· Showing ${visibleCount} of ${recommendations.length} recommendations found`;

            if (!currentSelectedIsVisible && firstVisibleIdx !== -1) {
                selectRouteCard(firstVisibleIdx);
            }
        }



        // Submit Real Journey Request
        function submitJourneyRequest() {
            const btn = document.getElementById('find-routes-btn');
            const loadingBox = document.getElementById('ai-loading-box');
            const resultsBox = document.getElementById('results-container');
            const queryInput = document.getElementById('journey-query').value.trim();

            if (!queryInput) {
                // Inline validation instead of alert if possible, or basic alert for Step 2
                resultsBox.innerHTML = `
                    <div class="alert alert-danger m-0 py-2.5 px-3 rounded-2" role="alert">
                        Please enter a journey description.
                    </div>
                `;
                return;
            }

            // Build natural language query
            let finalQuery = queryInput;

            const payload = {
                query: finalQuery
            };

            // Dates
            const depInput = document.getElementById('input-departure-time');
            const arrInput = document.getElementById('input-arrival-deadline');

            const formatLocalIso = (date) => {
                const tzOffset = -date.getTimezoneOffset();
                const diff = tzOffset >= 0 ? '+' : '-';
                const pad = n => `${Math.floor(Math.abs(n))}`.padStart(2, '0');
                
                return date.getFullYear() + '-' +
                    pad(date.getMonth() + 1) + '-' +
                    pad(date.getDate()) + 'T' +
                    pad(date.getHours()) + ':' +
                    pad(date.getMinutes()) + ':' +
                    pad(date.getSeconds()) + diff +
                    pad(tzOffset / 60) + ':' +
                    pad(tzOffset % 60);
            };

            let dDate = null;
            let aDate = null;

            if (depInput && depInput.value) {
                // value is "YYYY-MM-DDTHH:mm"
                dDate = new Date(depInput.value);
            }
            if (arrInput && arrInput.value) {
                aDate = new Date(arrInput.value);
            }

            const clearUI = () => {
                latestPlanResponse = null;
                const filterBar = document.getElementById('result-filter-bar');
                if (filterBar) filterBar.classList.add('d-none');
                document.querySelectorAll('#result-filter-container .pref-chip').forEach(btn => btn.classList.remove('active'));
                
                if (typeof drawRouteMap === 'function') {
                    drawRouteMap(null);
                }
                const weatherPanel = document.getElementById('weather-panel');
                if (weatherPanel) {
                    weatherPanel.innerHTML = `
                    <div class="text-center">
                        <i class="bi bi-cloud-sun text-muted mb-2" style="font-size: 24px;"></i>
                        <p class="text-muted m-0" style="font-size: 13px;">Weather information unavailable for this journey.</p>
                    </div>
                    `;
                }
            };

            // Removed requirement for explicit departure time when deadline is provided

            if (dDate && aDate && dDate.getTime() >= aDate.getTime()) {
                clearUI();
                resultsBox.innerHTML = `
                    <div class="alert alert-danger m-0 py-2.5 px-3 rounded-2" role="alert">
                        Please check your departure time and arrival deadline.
                    </div>
                `;
                return;
            }

            if (dDate && !isNaN(dDate.getTime())) {
                payload.departure_time = formatLocalIso(dDate);
            }
            if (aDate && !isNaN(aDate.getTime())) {
                payload.arrival_deadline = formatLocalIso(aDate);
            }

            // Update UI State
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> <span class="ms-2">Finding Routes...</span>`;
            
            loadingBox.classList.remove('d-none');
            resultsBox.style.opacity = '0.35';
            resultsBox.style.pointerEvents = 'none';

            fetch('/api/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json().then(data => ({status: res.status, ok: res.ok, data})).catch(() => ({status: res.status, ok: res.ok, data: {}})))
            .catch(err => ({status: 500, ok: false, data: {error: {message: 'Unable to reach the journey planning service.'}}}))
            .then(result => {
                btn.disabled = false;
                btn.innerHTML = `<i class="bi bi-search"></i> <span class="">Find Best Routes</span>`;
                loadingBox.classList.add('d-none');
                resultsBox.style.opacity = '1';
                resultsBox.style.pointerEvents = 'auto';

                if (!result.ok) {
                    let errorMsg = 'Something went wrong while planning your journey. Please try again.';
                    if (result.status === 400) {
                        errorMsg = result.data?.error?.message || 'Please check your trip information and try again.';
                    } else if (result.status === 422) {
                        errorMsg = result.data?.error?.message || "We couldn't find a suitable journey for this request. Try changing your locations or trip options.";
                    } else if (result.status === 500) {
                        errorMsg = result.data?.error?.message || 'Something went wrong while planning your journey. Please try again.';
                    } else {
                        errorMsg = result.data?.error?.message || errorMsg;
                    }
                    
                    // Clear stale state
                    clearUI();
                    
                    resultsBox.innerHTML = `
                        <div class="alert alert-danger border d-flex align-items-start gap-2.5 m-0 py-2.5 px-3 rounded-2" role="alert">
                            <i class="bi bi-exclamation-triangle-fill mt-0.5"></i>
                            <div style="font-size: 13px;">
                                <strong>Error</strong><br/>
                                ${errorMsg}
                            </div>
                        </div>
                    `;
                    return;
                }

                latestPlanResponse = result.data;
                const respData = latestPlanResponse.data || {};
                
                const getShortName = (locObj) => {
                    if (!locObj || !locObj.geocoding) return 'Unknown';
                    const full = locObj.geocoding.display_name || locObj.geocoding.query || 'Unknown Location';
                    return full.split(',')[0].trim();
                };
                
                const origin = getShortName(respData.origin);
                const dest = getShortName(respData.destination);
                const recommendations = respData.recommendations || [];

                let fastestIdx = -1, lowestCostIdx = -1, lessWalkingIdx = -1;
                if (recommendations.length > 0) {
                    let minTime = Infinity, minCost = Infinity, minWalk = Infinity;
                    recommendations.forEach((r, idx) => {
                        if (r.time_min != null && r.time_min < minTime) { minTime = r.time_min; fastestIdx = idx; }
                        if (r.cost_bdt != null && r.cost_bdt < minCost) { minCost = r.cost_bdt; lowestCostIdx = idx; }
                        if (r.walk_km != null && r.walk_km < minWalk) { minWalk = r.walk_km; lessWalkingIdx = idx; }
                    });
                }

                let routesHtml = recommendations.map((rec, i) => {
                    // Create formatted mode sequence
                    let modesString = 'N/A';
                    let modesHtml = '';
                    if (rec.mode_sequence) {
                        modesString = rec.mode_sequence.split('->').map(m => m.trim().charAt(0).toUpperCase() + m.trim().slice(1)).join(' → ');
                        const parts = rec.mode_sequence.split('->');
                        modesHtml = parts.map((m, idx) => {
                            m = m.trim().toLowerCase();
                            let icon = 'bi-signpost';
                            if (m === 'walk') icon = 'bi-person-walking';
                            if (m === 'metro' || m === 'train') icon = 'bi-train-front';
                            if (m === 'bus') icon = 'bi-bus-front';
                            
                            const arrow = idx < parts.length - 1 ? '<i class="bi bi-chevron-right text-muted mx-1" style="font-size: 12px;"></i>' : '';
                            return `<span class="route-step-pill ${m === 'metro' ? 'metro' : ''} ${m === 'bus' ? 'bus' : ''}"><i class="bi ${icon}"></i> ${m.charAt(0).toUpperCase() + m.slice(1)}</span>${arrow}`;
                        }).join('');
                    }

                    // Format ETA/Departure
                    let etaHtml = '';
                    if (rec.departure_time && rec.estimated_arrival_time) {
                        const dep = new Date(rec.departure_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        const arr = new Date(rec.estimated_arrival_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        
                        let lateness = '';
                        if (rec.minutes_late > 0) lateness = ` <span class="text-danger fw-bold">(${Math.ceil(rec.minutes_late)} min late)</span>`;
                        if (rec.minutes_early > 0) lateness = ` <span class="text-success fw-bold">(${Math.ceil(rec.minutes_early)} min early)</span>`;
                        
                        etaHtml = `
                        <div class="mb-3 p-2 bg-light rounded d-flex justify-content-between text-dark" style="font-size: 13px;">
                            <span><i class="bi bi-clock"></i> Departs: <strong>${dep}</strong></span>
                            <span>Arrives: <strong>${arr}</strong>${lateness}</span>
                        </div>
                        `;
                    } else if (rec.departure_time) {
                        const dep = new Date(rec.departure_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        etaHtml = `
                        <div class="mb-3 p-2 bg-light rounded d-flex justify-content-between text-dark" style="font-size: 13px;">
                            <span><i class="bi bi-clock"></i> Departs: <strong>${dep}</strong></span>
                        </div>
                        `;
                    }
                    
                    const isRecommended = (rec.rank === 1);
                    
                    // Route Data for Saving
                    const routeToSave = {
                        origin: origin,
                        destination: dest,
                        route_data: {
                            cost_bdt: rec.cost_bdt,
                            time_min: rec.time_min,
                            transfers: rec.transfers,
                            walk_km: rec.walk_km,
                            mode_sequence: rec.mode_sequence
                        }
                    };
                    const routeDataStr = encodeURIComponent(JSON.stringify(routeToSave));
                    const isSaved = savedRoutes.some(r => r.origin === origin && r.destination === dest && r.route_data && r.route_data.mode_sequence === rec.mode_sequence && r.route_data.time_min === rec.time_min);
                    const btnClass = isSaved ? 'btn-bookmark-action saved' : 'btn-bookmark-action';
                    const iconClass = isSaved ? 'bi bi-bookmark-fill' : 'bi bi-bookmark';


                    let labelsHtml = '';
                    if (isRecommended) labelsHtml += '<span class="badge bg-black text-white px-2 py-0.5 fw-semibold" style="font-size: 11px;">Recommended</span> ';
                    if (i === fastestIdx && !isRecommended) labelsHtml += '<span class="badge bg-light text-dark border px-2 py-0.5 fw-semibold" style="font-size: 11px;">Fastest</span> ';
                    if (i === lowestCostIdx && !isRecommended) labelsHtml += '<span class="badge bg-light text-dark border px-2 py-0.5 fw-semibold" style="font-size: 11px;">Lowest Cost</span> ';
                    if (i === lessWalkingIdx && !isRecommended) labelsHtml += '<span class="badge bg-light text-dark border px-2 py-0.5 fw-semibold" style="font-size: 11px;">Less Walking</span> ';

                    return `
                    <div class="uber-card p-3 mb-3 position-relative route-card-item" id="route-card-${i}" style="border: 2px solid ${isRecommended ? '#000' : '#E5E7EB'}; cursor: pointer;" onclick="selectRouteCard(${i})">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                <span class="fw-bold" style="font-size: 14px; color: #111111;">Route ${i+1}</span>
                                ${labelsHtml}
                            </div>
                            <div class="d-flex align-items-center gap-3">
                                <button aria-label="Save this route" class="${btnClass}" id="btn-save-${routeToSave.id}" onclick="toggleSaveRoute(this, '${routeDataStr}')" title="Save Route" type="button">
                                    <i class="${iconClass}"></i>
                                </button>
                            </div>
                        </div>
                        ${etaHtml}
                        <div class="d-flex align-items-center gap-1 flex-wrap mb-3">
                            ${modesHtml}
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col-6 col-md-3">
                                <div class="metric-box border p-2 rounded text-center">
                                    <span class="d-block text-muted" style="font-size:11px;">Travel Time</span>
                                    <span class="fw-bold" style="font-size:14px; color:#111;">${rec.time_min != null ? Math.round(rec.time_min * 10) / 10 : 'N/A'} min</span>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="metric-box border p-2 rounded text-center">
                                    <span class="d-block text-muted" style="font-size:11px;">Est. Cost</span>
                                    <span class="fw-bold" style="font-size:14px; color:#111;">${rec.cost_bdt != null ? '৳' + rec.cost_bdt : 'N/A'}</span>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="metric-box border p-2 rounded text-center">
                                    <span class="d-block text-muted" style="font-size:11px;">Transfers</span>
                                    <span class="fw-bold" style="font-size:14px; color:#111;">${rec.transfers != null ? rec.transfers : 'N/A'}</span>
                                </div>
                            </div>
                            <div class="col-6 col-md-3">
                                <div class="metric-box border p-2 rounded text-center">
                                    <span class="d-block text-muted" style="font-size:11px;">Walking</span>
                                    <span class="fw-bold" style="font-size:14px; color:var(--color-success);">${rec.walk_km != null ? rec.walk_km : 'N/A'} km</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `}).join('');

                const weatherPanel = document.getElementById('weather-panel');
                if (weatherPanel) {
                    if (respData.weather_available && respData.weather) {
                        const w = respData.weather;
                        weatherPanel.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="fw-bold" style="font-size: 14px; color: #111111;">Dhaka Transit Weather</span>
                        </div>
                        <div class="p-3 rounded-2 mb-0 d-flex justify-content-between align-items-center" style="background-color: #F9FAFB; border: 1px solid var(--border-color);">
                            <div class="d-flex align-items-center gap-2.5">
                                <i class="bi bi-cloud-sun text-dark" style="font-size: 28px;"></i>
                                <div>
                                    <span class="d-block fw-bold" style="font-size: 18px; color: #111111; line-height: 1.1;">${w.temperature_c != null ? Math.round(w.temperature_c) + '°C' : ''}</span>
                                    <span class="text-muted" style="font-size: 12px;">${w.condition || 'Unknown'}</span>
                                </div>
                            </div>
                        </div>
                        `;
                    } else {
                        weatherPanel.innerHTML = `
                        <div class="text-center">
                            <i class="bi bi-cloud-sun text-muted mb-2" style="font-size: 24px;"></i>
                            <p class="text-muted m-0" style="font-size: 13px;">Weather information unavailable.</p>
                        </div>
                        `;
                    }
                }

                let advisoryHtml = '';
                if (respData.advisory) {
                    advisoryHtml = `
                    <div class="p-3 rounded-3 d-flex align-items-start gap-2.5 mb-2" style="background-color: var(--color-amber-bg); border: 1px solid var(--color-amber-border);">
                        <i class="bi bi-info-circle-fill flex-shrink-0" style="color: var(--color-amber); font-size: 18px; margin-top: 1px;"></i>
                        <p class="m-0" style="font-size: 13px; color: #78350F; line-height: 1.4;">
                            ${respData.advisory}
                        </p>
                    </div>
                    `;
                }

                resultsBox.innerHTML = `
                    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 px-1 mb-2">
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <span class="fw-bold" style="font-size: 18px; color: #111111;">${origin}</span>
                            <i class="bi bi-arrow-right text-dark"></i>
                            <span class="fw-bold" style="font-size: 18px; color: #111111;">${dest}</span>
                            <span class="text-muted ms-1" style="font-size: 13px;" id="recommendations-count-text">· ${recommendations.length} recommendations found</span>
                        </div>
                    </div>
                    ${advisoryHtml}
                    ${routesHtml || '<div class="alert alert-warning border">No suitable routes were found. Try changing your journey details, timing, or preferences.</div>'}
                `;
                
                if (recommendations.length > 0) {
                    const filterBar = document.getElementById('result-filter-bar');
                    if (filterBar) filterBar.classList.remove('d-none');
                    document.querySelectorAll('#result-filter-container .pref-chip').forEach(btn => btn.classList.remove('active'));
                    selectRouteCard(0);
                } else {
                    const filterBar = document.getElementById('result-filter-bar');
                    if (filterBar) filterBar.classList.add('d-none');
                    drawRouteMap(null);
                }
            });
        }
        
        function loadTransitLines() {
            fetch('/api/transit-lines')
            .then(res => res.json())
            .then(data => {
                if (data.success && data.data) {
                    const container = document.getElementById('transit-lines-container');
                    if (!container) return;
                    let html = '';
                    data.data.forEach(line => {
                        html += `
                        <div class="col-12 col-md-6 line-item-card" data-category="${line.mode}">
                            <div class="uber-card h-100 p-4 d-flex flex-column justify-content-between">
                                <div>
                                    <div class="d-flex justify-content-between align-items-start mb-2">
                                        <div>
                                            <h3 class="fw-bold m-0" style="font-size: 18px; color: #111111;">${line.name}</h3>
                                        </div>
                                    </div>
                                    <div class="d-flex align-items-center gap-2 text-muted mb-3" style="font-size: 13px;">
                                        <i class="${line.mode === 'metro' ? 'bi-train-front' : 'bi-bus-front'}"></i>
                                        <span>Mode: ${line.mode.charAt(0).toUpperCase() + line.mode.slice(1)}</span>
                                        <span>·</span>
                                        <span>${line.stop_count} stops</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        `;
                    });
                    container.innerHTML = html;
                }
            })
            .catch(err => console.error("Could not load transit lines", err));
        }
        
        // Profile and Logout functions
        function toggleProfileDropdown(e) {
            if (e) e.stopPropagation();
            const dropdown = document.getElementById('profile-dropdown-menu');
            if (dropdown) {
                if (dropdown.classList.contains('d-none')) {
                    dropdown.classList.remove('d-none');
                } else {
                    dropdown.classList.add('d-none');
                }
            }
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('profile-dropdown-menu');
            const btn = document.getElementById('profile-avatar-btn');
            if (dropdown && !dropdown.classList.contains('d-none')) {
                if (!dropdown.contains(e.target) && (!btn || !btn.contains(e.target))) {
                    dropdown.classList.add('d-none');
                }
            }
        });
        
        function viewProfile(e) {
            if (e) e.stopPropagation();
            toggleProfileDropdown();
        }
        
        function handleLogout(e) {
            if (e) e.stopPropagation();
            
            const target = e.currentTarget;
            if (target) {
                target.style.opacity = '0.5';
                target.style.pointerEvents = 'none';
                target.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" style="width: 14px; height: 14px;"></span><span class="">Logging out...</span>`;
            }
        
            fetch('/api/auth/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/';
                } else {
                    if (target) {
                        target.style.opacity = '1';
                        target.style.pointerEvents = 'auto';
                        target.innerHTML = `<i class="bi bi-box-arrow-right flex-shrink-0" style="font-size: 15px; color: #DC2626;"></i><span class="">Log out</span>`;
                    }
                }
            })
            .catch(err => {
                if (target) {
                    target.style.opacity = '1';
                    target.style.pointerEvents = 'auto';
                    target.innerHTML = `<i class="bi bi-box-arrow-right flex-shrink-0" style="font-size: 15px; color: #DC2626;"></i><span class="">Log out</span>`;
                }
            });
        }

        // Initial setup on load
        document.addEventListener('DOMContentLoaded', () => {
            initMap();
            loadSavedRoutes();
            loadTransitLines();
        });