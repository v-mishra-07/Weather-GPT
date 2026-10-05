/**
 * navigation.js - Screen navigation for WeatherGPT SPA
 */

const SCREENS = ['splash', 'create-account', 'login', 'home', 'weather', 'forecast', 'chat', 'alerts', 'safe-route', 'climate', 'predict', 'emergency', 'explain', 'dashboard', 'profile'];

/**
 * Navigate to a screen by its ID (without the "screen-" prefix).
 * Hides all other screens, activates the target, updates the bottom nav,
 * and fires a custom "screenChanged" event so app.js can load data.
 * @param {string} screenId - one of the SCREENS values
 */
function navigateTo(screenId) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));

    // Show target screen
    const target = document.getElementById(`screen-${screenId}`);
    if (target) target.classList.add('active');

    // Bottom navigation: hide on splash screen and auth screens, show on main app screens
    const bottomNav = document.querySelector('.bottom-nav');
    if (bottomNav) {
        const hideNav = screenId === 'splash' || screenId === 'create-account' || screenId === 'login';
        bottomNav.style.display = hideNav ? 'none' : 'flex';
    }

    // Update bottom nav active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.screen === screenId);
    });

    // Store current screen globally for other modules
    window.currentScreen = screenId;

    // Sync URL hash so each page has its own direct shareable link
    try {
        if (window.location.hash !== `#${screenId}`) {
            history.replaceState(null, '', `#${screenId}`);
        }
    } catch (_) {}

    // Notify app.js (and any other listeners) that the screen changed
    const event = new CustomEvent('screenChanged', { detail: { screen: screenId } });
    document.dispatchEvent(event);
}

/**
 * Attach click listeners to every bottom-nav button and listen for hash changes.
 * Called once on DOMContentLoaded by app.js.
 */
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const screen = item.dataset.screen;
            if (screen) navigateTo(screen);
        });
    });

    // Listen for direct URL hash changes
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.replace('#', '');
        if (hash && SCREENS.includes(hash) && hash !== window.currentScreen) {
            navigateTo(hash);
        }
    });
}
