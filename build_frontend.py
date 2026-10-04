import os
import re

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

ensure_dir('templates')
ensure_dir('static/css')
ensure_dir('static/js')

######################################################################
# PLANNER
######################################################################

with open('prototype/planner_prototype.html', 'r', encoding='utf-8') as f:
    planner_html = f.read()

# Extract style
style_match = re.search(r'<style>(.*?)</style>', planner_html, re.DOTALL)
planner_css = style_match.group(1).strip()
planner_html = planner_html.replace(style_match.group(0), '<link href="{{ url_for(\'static\', filename=\'css/planner.css\') }}" rel="stylesheet" />')

# Extract script
script_match = re.search(r'<script>(.*?)</script>', planner_html, re.DOTALL)
planner_js = script_match.group(1).strip()
planner_html = planner_html.replace(script_match.group(0), '<script src="{{ url_for(\'static\', filename=\'js/planner.js\') }}"></script>')

# Remove fake UI claims in planner
# "micro-congestion" -> "weather-aware ranking"
planner_html = planner_html.replace('Checking weather &amp; micro-congestion', 'Checking weather &amp; ranking routes')
# "Live Radar" -> "Weather Data"
planner_html = planner_html.replace('Live Radar', 'Weather Data')
# "100% on-time frequency" -> "high reliability"
planner_html = planner_html.replace('100% on-time frequency', 'high reliability')

# Remove "Use My Current Location" button or disable it
# The instructions say "Preferred: remove the button entirely for now."
gps_btn_pattern = r'<div class="align-self-start align-self-md-center">[\s]*<button[^>]*id="gps-btn"[^>]*>[\s\S]*?</button>[\s]*</div>'
planner_html = re.sub(gps_btn_pattern, '', planner_html)

# Add logout navigation route
planner_js = planner_js.replace("alert('Logging out... Redirecting to Authentication page.');", "window.location.href = '/';")

with open('static/css/planner.css', 'w', encoding='utf-8') as f:
    f.write(planner_css)

with open('static/js/planner.js', 'w', encoding='utf-8') as f:
    f.write(planner_js)

with open('templates/planner.html', 'w', encoding='utf-8') as f:
    f.write(planner_html)


######################################################################
# AUTH
######################################################################

# We translate Tailwind to Bootstrap 5
auth_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta content="width=device-width, initial-scale=1.0" name="viewport" />
    <title>Smart Transit — Dhaka Multimodal Transit</title>
    <!-- Inter Google Font -->
    <link href="https://fonts.googleapis.com" rel="preconnect" />
    <link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&amp;display=swap" rel="stylesheet" />
    <!-- Material Symbols Outlined -->
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet" />
    <!-- Bootstrap 5 CSS & Bootstrap Icons -->
    <link crossorigin="anonymous" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet" />
    <link href="{{ url_for('static', filename='css/auth.css') }}" rel="stylesheet" />
</head>
<body class="bg-light text-dark d-flex flex-column min-vh-100 font-sans">

    <!-- Top Navigation Header -->
    <header class="w-100 bg-white border-bottom sticky-top">
        <div class="container-fluid max-w-7xl px-3 px-sm-4 h-64 d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-3">
                <div class="logo-box">
                    <svg class="w-100 h-100" fill="none" viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 36C12 36 17 20 25 20C33 20 31 40 39 24" stroke="#FFFFFF" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5"></path>
                        <circle cx="12" cy="36" fill="#FFFFFF" r="3.5"></circle>
                        <circle cx="25" cy="20" fill="#2563EB" r="3.5"></circle>
                        <circle cx="39" cy="24" fill="#000000" r="4.5" stroke="#FFFFFF" stroke-width="2.5"></circle>
                        <path d="M36 11L37 13.8L40 15L37 16.2L36 19L35 16.2L32 15L35 13.8L36 11Z" fill="#FFFFFF"></path>
                    </svg>
                </div>
                <div>
                    <span class="fs-6 fw-black text-black d-flex align-items-center gap-1">
                        SmartTransit <span class="badge bg-black text-white px-2 py-1 lh-1 text-uppercase fw-bold rounded-1" style="font-size: 10px; letter-spacing: 0.1em;">Dhaka</span>
                    </span>
                </div>
            </div>
            <div class="d-flex align-items-center gap-3">
                <div class="d-none d-sm-flex align-items-center gap-2 px-3 py-1 rounded-pill bg-light border text-dark fw-semibold" style="font-size: 12px;">
                    <span class="pulse-dot"></span>
                    <span>MRT Line 6 Live</span>
                </div>
                <button aria-label="Live network status" class="nav-icon-btn d-flex align-items-center justify-content-center">
                    <span class="material-symbols-outlined fs-5">sensors</span>
                </button>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-grow-1 w-100 max-w-7xl mx-auto d-flex align-items-center justify-content-center p-3 p-sm-4 p-lg-5">
        <div class="row w-100 justify-content-center align-items-stretch g-4 g-lg-5">
            <!-- Left Canvas -->
            <section class="col-lg-6 d-none d-lg-flex flex-column justify-content-between p-4 p-xl-5 bg-white rounded-4 border shadow-sm position-relative overflow-hidden">
                <div>
                    <div class="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill bg-black text-white text-uppercase fw-bold mb-4" style="font-size: 12px; letter-spacing: 0.05em;">
                        <i class="bi bi-cpu-fill text-primary"></i>
                        <span>AI Multimodal Mobility</span>
                    </div>
                    <h1 class="display-6 fw-black text-dark mb-3 lh-sm" style="letter-spacing: -0.03em;">
                        AI-Powered Multimodal Journey Planning for Dhaka
                    </h1>
                    <p class="text-muted fw-normal" style="font-size: 16px;">
                        Estimated multimodal route planning across MRT Line 6, digital buses, and rapid feeder transit.
                    </p>
                </div>
                <!-- Illustration Image Container -->
                <div class="my-4 rounded-4 border bg-light p-2 d-flex align-items-center justify-content-center overflow-hidden">
                    <img alt="Smart Transit Dhaka Minimal Illustration" class="img-fluid rounded-3" style="max-height: 340px; transition: transform 0.3s ease;" src="https://lh3.googleusercontent.com/aida/AEtjO1U1mdUNrq2oQIhm0xnPgpfcdP5FPePtrwZm5bdzCGjKBIvthXlq6gDFShhLJUJq9yNT_LWvf0HcKR3g7YwMFJMhiCCEWQwuqnKNg3PkmuGFMd3wA22I92TDRfcPfUYRlxaSyIMmOc2Q7guSfOSEkqGi5fvAfyvOSKyoUe4y26LavYaYTVZgenfKv_aghYi-z77MLOUmKltO8eacw42o-kBWdSCPGZpQ4hEKbKYAonh47f_c7biaqewglEQ" />
                </div>
                <!-- Trust Metrics -->
                <div class="row g-2 pt-4 border-top">
                    <div class="col-4">
                        <div class="p-3 bg-light rounded-3 border h-100">
                            <p class="fs-5 fw-black text-black mb-0 lh-1">16 Stns</p>
                            <p class="text-muted fw-medium mb-0 mt-1" style="font-size: 12px;">MRT-6 Live Sync</p>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="p-3 bg-light rounded-3 border h-100">
                            <p class="fs-5 fw-black text-black mb-0 lh-1">Smart</p>
                            <p class="text-muted fw-medium mb-0 mt-1" style="font-size: 12px;">AI Multimodal</p>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="p-3 bg-light rounded-3 border h-100">
                            <p class="fs-5 fw-black text-primary mb-0 lh-1">Fast</p>
                            <p class="text-muted fw-medium mb-0 mt-1" style="font-size: 12px;">Route Generation</p>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Right Canvas (Auth Card) -->
            <section class="col-12 col-md-8 col-lg-6 d-flex align-items-center justify-content-center">
                <div class="w-100 bg-white rounded-4 border p-4 p-sm-5 shadow-sm max-w-auth mx-auto">
                    <!-- Branding -->
                    <div class="d-flex flex-column align-items-center text-center mb-4">
                        <div class="mb-2 d-flex align-items-center justify-content-center" style="height: 56px;">
                            <img alt="Smart Transit Minimal Monochrome Logo" class="img-fluid h-100" src="https://lh3.googleusercontent.com/aida/AEtjO1VElE25e92syAuSdUP5MOe39p8U_r5gjozL4spVZYxJSOr-iBOwk16pZcDYFBRP3i0dZI-Hc3hce3F27RM2Nicvv4AOSW82VM4PqG2T841HIN66Hlv6SpJdmgYZUNH9KugA8hOTnk5pGR6Y2-8AZPJW6lE-ObVmOuI3BjgpWE4BfAKiPySGGSrjNyix41kEbMifpfv_C56UHKQQpnpla-XNZ_Lw7zDEQEEFsPYnOnA3IsuIIJVtZXERilM" />
                        </div>
                        <h2 class="fs-4 fw-black text-dark mb-1 lh-sm" style="letter-spacing: -0.03em;">
                            Travel Smarter Across Dhaka
                        </h2>
                        <p class="text-muted fw-medium mb-0" style="font-size: 14px;">
                            Log in or create an account to start planning better journeys.
                        </p>
                    </div>

                    <!-- Dual Action Tabs -->
                    <div class="row g-2 p-1 bg-light rounded-3 border mb-4 mx-0" role="tablist">
                        <div class="col-6 p-0">
                            <button id="tab-login-btn" onclick="switchToTab('login')" class="btn w-100 btn-black fw-bold py-2 rounded-2" type="button" aria-selected="true">Log In</button>
                        </div>
                        <div class="col-6 p-0">
                            <button id="tab-signup-btn" onclick="switchToTab('signup')" class="btn w-100 btn-light text-dark fw-bold py-2 rounded-2" type="button" aria-selected="false">Sign Up</button>
                        </div>
                    </div>

                    <!-- Alert Box -->
                    <div id="auth-alert" class="d-none alert border fw-semibold d-flex align-items-center gap-2 py-2 px-3 mb-4 rounded-3" style="font-size: 12px;"></div>

                    <!-- 1. LOGIN FORM -->
                    <form id="login-form" novalidate onsubmit="handleAuthSubmit(event, 'login')">
                        <div class="mb-3">
                            <h3 class="fs-6 fw-extrabold text-dark mb-0">Welcome Back</h3>
                            <p class="text-muted mb-0" style="font-size: 12px;">Log in to continue to Smart Transit.</p>
                        </div>

                        <!-- Email -->
                        <div class="mb-3">
                            <label for="login-email" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Email Address</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-envelope"></i>
                                </span>
                                <input type="email" id="login-email" class="form-control bg-white ps-5 text-dark" placeholder="example@gmail.com" autocomplete="email" />
                            </div>
                            <p id="login-email-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Password -->
                        <div class="mb-3">
                            <label for="login-password" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Password</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-shield-lock"></i>
                                </span>
                                <input type="password" id="login-password" class="form-control bg-white ps-5 pe-5 text-dark" placeholder="Enter your password" autocomplete="current-password" />
                                <button type="button" class="btn position-absolute top-50 end-0 translate-middle-y pe-3 text-muted border-0 shadow-none" onclick="togglePasswordVisibility('login-password', this)" aria-label="Toggle password visibility">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </div>
                            <p id="login-password-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Remember & Forgot Password -->
                        <div class="d-flex align-items-center justify-content-between mb-4">
                            <div class="form-check m-0">
                                <input class="form-check-input border-secondary" type="checkbox" id="login-remember">
                                <label class="form-check-label text-muted fw-medium" for="login-remember" style="font-size: 12px; cursor: pointer;">
                                    Remember me
                                </label>
                            </div>
                            <a href="javascript:void(0)" onclick="handleForgotPassword()" class="text-dark fw-semibold text-decoration-none border-bottom border-dark pb-0" style="font-size: 12px;">Forgot Password?</a>
                        </div>

                        <!-- Submit CTA -->
                        <button type="submit" id="login-submit-btn" class="btn btn-black w-100 py-3 fw-bold d-flex align-items-center justify-content-center gap-2 rounded-3">
                            <span>Log In</span>
                            <i class="bi bi-arrow-right fw-bold"></i>
                        </button>

                        <div class="text-center mt-3">
                            <p class="text-muted mb-0" style="font-size: 12px;">
                                Don't have an account? 
                                <button type="button" class="btn btn-link p-0 text-dark fw-bold text-decoration-none ms-1 border-0" onclick="switchToTab('signup')">Sign Up</button>
                            </p>
                        </div>
                    </form>

                    <!-- 2. SIGN UP FORM -->
                    <form id="signup-form" class="d-none" novalidate onsubmit="handleAuthSubmit(event, 'signup')">
                        <div class="mb-3">
                            <h3 class="fs-6 fw-extrabold text-dark mb-0">Create Your Account</h3>
                            <p class="text-muted mb-0" style="font-size: 12px;">Join Smart Transit and start planning smarter journeys.</p>
                        </div>

                        <!-- Full Name -->
                        <div class="mb-3">
                            <label for="signup-name" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Full Name</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-person"></i>
                                </span>
                                <input type="text" id="signup-name" class="form-control bg-white ps-5 text-dark" placeholder="Enter your full name" autocomplete="name" />
                            </div>
                            <p id="signup-name-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Email -->
                        <div class="mb-3">
                            <label for="signup-email" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Email Address</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-envelope"></i>
                                </span>
                                <input type="email" id="signup-email" class="form-control bg-white ps-5 text-dark" placeholder="example@gmail.com" autocomplete="email" />
                            </div>
                            <p id="signup-email-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Password -->
                        <div class="mb-3">
                            <label for="signup-password" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Password</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-lock"></i>
                                </span>
                                <input type="password" id="signup-password" class="form-control bg-white ps-5 pe-5 text-dark" placeholder="Create a password" />
                                <button type="button" class="btn position-absolute top-50 end-0 translate-middle-y pe-3 text-muted border-0 shadow-none" onclick="togglePasswordVisibility('signup-password', this)">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </div>
                            <p id="signup-password-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Confirm Password -->
                        <div class="mb-3">
                            <label for="signup-confirm-password" class="form-label text-dark fw-bold text-uppercase mb-1" style="font-size: 11px; letter-spacing: 0.05em;">Confirm Password</label>
                            <div class="position-relative">
                                <span class="position-absolute top-50 start-0 translate-middle-y ps-3 text-muted">
                                    <i class="bi bi-shield-check"></i>
                                </span>
                                <input type="password" id="signup-confirm-password" class="form-control bg-white ps-5 pe-5 text-dark" placeholder="Re-enter your password" />
                                <button type="button" class="btn position-absolute top-50 end-0 translate-middle-y pe-3 text-muted border-0 shadow-none" onclick="togglePasswordVisibility('signup-confirm-password', this)">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </div>
                            <p id="signup-confirm-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Terms Checkbox -->
                        <div class="mb-4">
                            <div class="form-check m-0">
                                <input class="form-check-input border-secondary mt-1" type="checkbox" id="signup-terms">
                                <label class="form-check-label text-muted lh-sm" for="signup-terms" style="font-size: 12px; cursor: pointer;">
                                    I agree to the <a href="javascript:void(0)" class="text-dark fw-semibold text-decoration-underline">Terms and Privacy Policy</a>.
                                </label>
                            </div>
                            <p id="signup-terms-err" class="d-none text-danger fw-medium mt-1 mb-0" style="font-size: 12px;"></p>
                        </div>

                        <!-- Submit CTA -->
                        <button type="submit" id="signup-submit-btn" class="btn btn-black w-100 py-3 fw-bold d-flex align-items-center justify-content-center gap-2 rounded-3">
                            <span>Create Account</span>
                            <i class="bi bi-arrow-right fw-bold"></i>
                        </button>

                        <div class="text-center mt-3">
                            <p class="text-muted mb-0" style="font-size: 12px;">
                                Already have an account? 
                                <button type="button" class="btn btn-link p-0 text-dark fw-bold text-decoration-none ms-1 border-0" onclick="switchToTab('login')">Log In</button>
                            </p>
                        </div>
                    </form>

                    <!-- Footer Note -->
                    <div class="mt-4 pt-3 border-top d-flex align-items-center justify-content-between text-muted" style="font-size: 12px;">
                        <span class="d-flex align-items-center gap-1 fw-medium">
                            <i class="bi bi-credit-card-2-front text-dark"></i>
                            Dhaka Rapid Pass sync
                        </span>
                        <a href="javascript:void(0)" onclick="alert('Rapid Pass / MRT pass integration can be activated after logging in to your Journey Planner.')" class="fw-bold text-dark text-decoration-none border-bottom border-dark pb-0">Learn More</a>
                    </div>
                </div>
            </section>
        </div>
    </main>

    <!-- Footer -->
    <footer class="w-100 bg-white border-top py-3 text-muted" style="font-size: 12px;">
        <div class="container-fluid max-w-7xl px-4 d-flex flex-column flex-sm-row align-items-center justify-content-between gap-2">
            <div class="d-flex align-items-center gap-2">
                <span class="d-inline-block rounded-circle bg-black" style="width: 8px; height: 8px;"></span>
                <span class="fw-medium">Estimated Multimodal Routes</span>
            </div>
            <p class="fw-medium m-0">© Smart Transit Dhaka. Minimal Multimodal Engine.</p>
        </div>
    </footer>

    <script src="{{ url_for('static', filename='js/auth.js') }}"></script>
</body>
</html>"""

auth_css = """
body { font-family: 'Inter', -apple-system, sans-serif; }
.fw-black { font-weight: 900; }
.fw-extrabold { font-weight: 800; }
.max-w-7xl { max-width: 80rem; }
.max-w-auth { max-width: 420px; }
.h-64 { height: 64px; }
.logo-box {
    width: 36px; height: 36px;
    border-radius: 12px;
    background-color: #000;
    display: flex; align-items: center; justify-content: center;
    padding: 6px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.nav-icon-btn {
    width: 36px; height: 36px;
    border-radius: 12px;
    border: 1px solid #dee2e6;
    background-color: #fff;
    color: #212529;
    transition: background-color 0.2s;
}
.nav-icon-btn:hover { background-color: #f8f9fa; }
.pulse-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background-color: #198754;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(25, 135, 84, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0); }
}
.btn-black {
    background-color: #000;
    color: #fff;
    border: none;
    transition: all 0.2s;
}
.btn-black:hover {
    background-color: #222;
    color: #fff;
}
.btn-black:active {
    transform: scale(0.98);
}
.btn-light {
    background-color: transparent;
    border: none;
    transition: all 0.2s;
}
.btn-light:hover {
    background-color: rgba(255,255,255,0.6);
    color: #000;
}
.form-control {
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    color: #111111;
    min-height: 46px;
}
.form-control::placeholder {
    color: #9CA3AF;
    opacity: 1;
}
.form-control:focus {
    border-color: #000;
    box-shadow: 0 0 0 1px #000;
}
.position-absolute i {
    font-size: 15px;
}
"""

auth_js = """
const tabLoginBtn = document.getElementById('tab-login-btn');
const tabSignupBtn = document.getElementById('tab-signup-btn');
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const alertBox = document.getElementById('auth-alert');

function switchToTab(tab) {
    alertBox.classList.add('d-none');
    if (tab === 'login') {
        tabLoginBtn.className = 'btn w-100 btn-black fw-bold py-2 rounded-2';
        tabLoginBtn.setAttribute('aria-selected', 'true');

        tabSignupBtn.className = 'btn w-100 btn-light text-dark fw-bold py-2 rounded-2';
        tabSignupBtn.setAttribute('aria-selected', 'false');

        loginForm.classList.remove('d-none');
        signupForm.classList.add('d-none');
    } else {
        tabSignupBtn.className = 'btn w-100 btn-black fw-bold py-2 rounded-2';
        tabSignupBtn.setAttribute('aria-selected', 'true');

        tabLoginBtn.className = 'btn w-100 btn-light text-dark fw-bold py-2 rounded-2';
        tabLoginBtn.setAttribute('aria-selected', 'false');

        signupForm.classList.remove('d-none');
        loginForm.classList.add('d-none');
    }
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}

function showAlert(msg, isSuccess = true) {
    alertBox.className = isSuccess
        ? 'alert border fw-semibold d-flex align-items-center gap-2 py-2 px-3 mb-4 rounded-3 bg-black text-white border-dark'
        : 'alert border fw-semibold d-flex align-items-center gap-2 py-2 px-3 mb-4 rounded-3 bg-danger-subtle text-danger border-danger-subtle';
    alertBox.innerHTML = `
<i class="bi ${isSuccess ? 'bi-check-circle-fill text-primary' : 'bi-exclamation-octagon-fill'}"></i>
<span>${msg}</span>
`;
    alertBox.classList.remove('d-none');
}

function handleForgotPassword() {
    const email = document.getElementById('login-email').value;
    if (!email || !email.includes('@')) {
        alert('Please enter your email address in the input above first.');
    } else {
        showAlert('Password reset link sent to ' + email, true);
    }
}

function navigateToJourneyPlanner() {
    window.location.href = '/planner';
}

function handleAuthSubmit(e, formType) {
    e.preventDefault();
    let isValid = true;

    if (formType === 'login') {
        const email = document.getElementById('login-email');
        const emailErr = document.getElementById('login-email-err');
        const pass = document.getElementById('login-password');
        const passErr = document.getElementById('login-password-err');

        if (!email.value || !email.value.includes('@') || !email.value.includes('.')) {
            emailErr.textContent = 'Please enter a valid email address.';
            emailErr.classList.remove('d-none');
            email.classList.add('border-danger');
            isValid = false;
        } else {
            emailErr.classList.add('d-none');
            email.classList.remove('border-danger');
        }

        if (!pass.value || pass.value.length < 6) {
            passErr.textContent = 'Password must be at least 6 characters.';
            passErr.classList.remove('d-none');
            pass.classList.add('border-danger');
            isValid = false;
        } else {
            passErr.classList.add('d-none');
            pass.classList.remove('border-danger');
        }

        if (isValid) {
            const btn = document.getElementById('login-submit-btn');
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Authenticating...`;

            setTimeout(() => {
                showAlert('Login successful! Redirecting to Journey Planner...', true);
                setTimeout(() => {
                    navigateToJourneyPlanner();
                    btn.disabled = false;
                    btn.innerHTML = `<span>Log In</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                }, 700);
            }, 600);
        }
    } else if (formType === 'signup') {
        const name = document.getElementById('signup-name');
        const nameErr = document.getElementById('signup-name-err');
        const email = document.getElementById('signup-email');
        const emailErr = document.getElementById('signup-email-err');
        const pass = document.getElementById('signup-password');
        const passErr = document.getElementById('signup-password-err');
        const confirm = document.getElementById('signup-confirm-password');
        const confirmErr = document.getElementById('signup-confirm-err');
        const terms = document.getElementById('signup-terms');
        const termsErr = document.getElementById('signup-terms-err');

        if (!name.value.trim()) {
            nameErr.textContent = 'Please enter your full name.';
            nameErr.classList.remove('d-none');
            name.classList.add('border-danger');
            isValid = false;
        } else {
            nameErr.classList.add('d-none');
            name.classList.remove('border-danger');
        }

        if (!email.value || !email.value.includes('@') || !email.value.includes('.')) {
            emailErr.textContent = 'Please enter a valid email address.';
            emailErr.classList.remove('d-none');
            email.classList.add('border-danger');
            isValid = false;
        } else {
            emailErr.classList.add('d-none');
            email.classList.remove('border-danger');
        }

        if (!pass.value || pass.value.length < 8) {
            passErr.textContent = 'Password must be at least 8 characters.';
            passErr.classList.remove('d-none');
            pass.classList.add('border-danger');
            isValid = false;
        } else {
            passErr.classList.add('d-none');
            pass.classList.remove('border-danger');
        }

        if (pass.value !== confirm.value) {
            confirmErr.textContent = 'Passwords do not match.';
            confirmErr.classList.remove('d-none');
            confirm.classList.add('border-danger');
            isValid = false;
        } else {
            confirmErr.classList.add('d-none');
            confirm.classList.remove('border-danger');
        }

        if (!terms.checked) {
            termsErr.textContent = 'You must agree to the Terms and Privacy Policy.';
            termsErr.classList.remove('d-none');
            isValid = false;
        } else {
            termsErr.classList.add('d-none');
        }

        if (isValid) {
            const btn = document.getElementById('signup-submit-btn');
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating account...`;

            setTimeout(() => {
                showAlert('Account created! Entering Journey Planner...', true);
                setTimeout(() => {
                    navigateToJourneyPlanner();
                    btn.disabled = false;
                    btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                }, 700);
            }, 600);
        }
    }
}
"""

with open('static/css/auth.css', 'w', encoding='utf-8') as f:
    f.write(auth_css)

with open('static/js/auth.js', 'w', encoding='utf-8') as f:
    f.write(auth_js)

with open('templates/auth.html', 'w', encoding='utf-8') as f:
    f.write(auth_html)
