// ============================================
// API BASE URL (Auto-detect Vercel URL)
// ============================================
const API_BASE = window.location.origin;

// ============================================
// HERO SLIDER
// ============================================
let currentSlide = 0;
let heroSlides = [];
let autoSlideInterval;

async function loadHeroSlider() {
    try {
        const response = await fetch(`${API_BASE}/api/featured`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            heroSlides = data.data;
            renderHeroSlider();
            startAutoSlide();
        }
    } catch (error) {
        console.error('Error loading hero slider:', error);
    }
}

function renderHeroSlider() {
    const track = document.getElementById('heroTrack');
    const dots = document.getElementById('heroDots');
    
    track.innerHTML = heroSlides.map((slide, index) => `
        <div class="hero-slide" style="background-image: url('${slide.image}')">
            <div class="hero-slide-tag">${slide.tag || 'New'}</div>
            <div class="hero-slide-content">
                <h2>${slide.title}</h2>
                <a href="/drama/${slide.slug}" class="watch-btn">Watch Now</a>
            </div>
        </div>
    `).join('');
    
    dots.innerHTML = heroSlides.map((_, index) => `
        <button class="hero-dot ${index === 0 ? 'active' : ''}" onclick="goToSlide(${index})"></button>
    `).join('');
}

function goToSlide(index) {
    currentSlide = index;
    const track = document.getElementById('heroTrack');
    track.style.transform = `translateX(-${currentSlide * 100}%)`;
    
    document.querySelectorAll('.hero-dot').forEach((dot, i) => {
        dot.classList.toggle('active', i === currentSlide);
    });
}

function nextSlide() {
    goToSlide((currentSlide + 1) % heroSlides.length);
}

function prevSlide() {
    goToSlide((currentSlide - 1 + heroSlides.length) % heroSlides.length);
}

function startAutoSlide() {
    clearInterval(autoSlideInterval);
    autoSlideInterval = setInterval(nextSlide, 5000);
}

// ============================================
// LOAD LATEST DRAMAS
// ============================================
async function loadLatestDramas() {
    try {
        const response = await fetch(`${API_BASE}/api/latest`);
        const data = await response.json();
        
        if (data.success) {
            renderDramas('latestShelf', data.data.slice(0, 10));
        }
    } catch (error) {
        console.error('Error loading latest dramas:', error);
    }
}

// ============================================
// LOAD FEATURED DRAMAS
// ============================================
async function loadFeaturedDramas() {
    try {
        const response = await fetch(`${API_BASE}/api/dramas?limit=10`);
        const data = await response.json();
        
        if (data.success) {
            renderDramas('featuredShelf', data.data);
        }
    } catch (error) {
        console.error('Error loading featured dramas:', error);
    }
}

// ============================================
// LOAD BY CATEGORY
// ============================================
async function loadCategory(category) {
    try {
        document.getElementById('categoryTitle').textContent = 
            category.charAt(0).toUpperCase() + category.slice(1) + ' Dramas';
        
        const response = await fetch(`${API_BASE}/api/category/${category}`);
        const data = await response.json();
        
        if (data.success) {
            renderDramas('categoryShelf', data.data.slice(0, 10));
        }
    } catch (error) {
        console.error('Error loading category:', error);
    }
}

// ============================================
// LOAD ALL DRAMAS
// ============================================
async function loadAll() {
    try {
        const response = await fetch(`${API_BASE}/api/dramas?limit=30`);
        const data = await response.json();
        
        if (data.success) {
            renderDramas('categoryShelf', data.data);
            document.getElementById('categoryTitle').textContent = 'All Dramas';
        }
    } catch (error) {
        console.error('Error loading all dramas:', error);
    }
}

// ============================================
// RENDER DRAMAS
// ============================================
function renderDramas(containerId, dramas) {
    const container = document.getElementById(containerId);
    
    if (!dramas || dramas.length === 0) {
        container.innerHTML = '<div class="loading">No dramas found</div>';
        return;
    }
    
    container.innerHTML = dramas.map(drama => `
        <a href="/drama/${drama.slug}" class="drama-card">
            <div class="thumbnail">
                <img src="${drama.image}" alt="${drama.title}" loading="lazy">
                <span class="episode-badge">${drama.episode || 'New'}</span>
            </div>
            <div class="info">
                <div class="title">${drama.title}</div>
            </div>
        </a>
    `).join('');
}

// ============================================
// SEARCH DRAMAS
// ============================================
async function searchDramas(event) {
    if (event && event.key && event.key !== 'Enter') return;
    
    const query = document.getElementById('searchInput').value.trim();
    const resultsContainer = document.getElementById('searchResults');
    
    if (!query) {
        resultsContainer.innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            resultsContainer.innerHTML = data.data.map(drama => `
                <a href="/drama/${drama.slug}" class="search-result-item">
                    <img src="${drama.image}" alt="${drama.title}">
                    <div class="info">
                        <div class="title">${drama.title}</div>
                        <div class="episode">${drama.episode || 'New'}</div>
                    </div>
                </a>
            `).join('');
        } else {
            resultsContainer.innerHTML = '<div class="loading">No results found</div>';
        }
    } catch (error) {
        console.error('Error searching:', error);
        resultsContainer.innerHTML = '<div class="loading">Search failed</div>';
    }
}

// ============================================
// TOGGLE SEARCH
// ============================================
function toggleSearch() {
    const searchBox = document.getElementById('searchBox');
    searchBox.classList.toggle('hidden');
    if (!searchBox.classList.contains('hidden')) {
        document.getElementById('searchInput').focus();
    }
}

// ============================================
// THEME TOGGLE
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    
    // Load saved theme
    const savedTheme = localStorage.getItem('AsiaStream-theme') || 'dark';
    document.documentElement.classList.add(savedTheme + '-theme');
    themeToggle.checked = savedTheme === 'light';
    
    themeToggle.addEventListener('change', function() {
        const theme = this.checked ? 'light' : 'dark';
        document.documentElement.classList.remove('dark-theme', 'light-theme');
        document.documentElement.classList.add(theme + '-theme');
        localStorage.setItem('AsiaStream-theme', theme);
    });
});

// ============================================
// KEYBOARD SHORTCUTS
// ============================================
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleSearch();
    }
    if (e.key === 'Escape') {
        const searchBox = document.getElementById('searchBox');
        if (!searchBox.classList.contains('hidden')) {
            searchBox.classList.add('hidden');
        }
    }
});
