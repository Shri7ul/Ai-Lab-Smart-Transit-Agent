
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
    // Show the modal overlay
    const overlay = document.getElementById('auth-modal-overlay');
    const forgotModal = document.getElementById('forgot-password-modal');
    
    // reset form state
    document.getElementById('forgot-form').reset();
    document.getElementById('forgot-form').classList.remove('d-none');
    document.getElementById('forgot-feedback-success').classList.add('d-none');
    document.getElementById('forgot-feedback-error').classList.add('d-none');
    const submitBtn = document.getElementById('forgot-submit-btn');
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Send Reset Link</span> <i class="bi bi-arrow-right fw-bold"></i>`;
    
    // Copy email from login input if present
    const loginEmail = document.getElementById('login-email').value;
    if (loginEmail && loginEmail.includes('@')) {
        document.getElementById('forgot-email').value = loginEmail;
    }
    
    overlay.classList.remove('d-none');
    forgotModal.classList.remove('d-none');
    
    // Trigger animation
    setTimeout(() => {
        overlay.style.opacity = '1';
        forgotModal.style.transform = 'scale(1)';
    }, 10);
}

function closeAuthModal() {
    const overlay = document.getElementById('auth-modal-overlay');
    const forgotModal = document.getElementById('forgot-password-modal');
    const resetModal = document.getElementById('reset-password-modal');
    
    overlay.style.opacity = '0';
    forgotModal.style.transform = 'scale(0.95)';
    resetModal.style.transform = 'scale(0.95)';
    
    setTimeout(() => {
        overlay.classList.add('d-none');
        forgotModal.classList.add('d-none');
        resetModal.classList.add('d-none');
    }, 300);
}

function closeAuthModalAndLogin() {
    closeAuthModal();
    switchToTab('login');
}

function requestNewResetLink() {
    document.getElementById('reset-password-modal').classList.add('d-none');
    document.getElementById('reset-password-modal').style.transform = 'scale(0.95)';
    
    document.getElementById('forgot-password-modal').classList.remove('d-none');
    setTimeout(() => {
        document.getElementById('forgot-password-modal').style.transform = 'scale(1)';
    }, 10);
}

function submitForgotPassword(e) {
    e.preventDefault();
    const email = document.getElementById('forgot-email').value;
    const errorAlert = document.getElementById('forgot-feedback-error');
    const errorText = document.getElementById('forgot-error-text');
    
    if (!email || !email.includes('@') || !email.includes('.')) {
        errorText.textContent = 'Please enter a valid email address.';
        errorAlert.classList.remove('d-none');
        return;
    }
    errorAlert.classList.add('d-none');
    
    const btn = document.getElementById('forgot-submit-btn');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...`;
    
    fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById('forgot-form').classList.add('d-none');
            document.getElementById('forgot-feedback-success').classList.remove('d-none');
        } else {
            errorText.textContent = data.error?.message || 'Unable to send a reset link right now. Please try again.';
            errorAlert.classList.remove('d-none');
            btn.disabled = false;
            btn.innerHTML = `<span>Send Reset Link</span> <i class="bi bi-arrow-right fw-bold"></i>`;
        }
    })
    .catch(err => {
        errorText.textContent = 'Unable to send a reset link right now. Please try again.';
        errorAlert.classList.remove('d-none');
        btn.disabled = false;
        btn.innerHTML = `<span>Send Reset Link</span> <i class="bi bi-arrow-right fw-bold"></i>`;
    });
}

// Check for recovery token on load
document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.substring(1);
    if (hash && hash.includes('type=recovery') && hash.includes('access_token=')) {
        const params = new URLSearchParams(hash);
        const accessToken = params.get('access_token');
        
        if (accessToken) {
            // Remove token from URL
            window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
            
            // Store temporarily on the form element for submission
            document.getElementById('reset-form').dataset.token = accessToken;
            
            // Show reset modal
            const overlay = document.getElementById('auth-modal-overlay');
            const resetModal = document.getElementById('reset-password-modal');
            
            overlay.classList.remove('d-none');
            resetModal.classList.remove('d-none');
            
            setTimeout(() => {
                overlay.style.opacity = '1';
                resetModal.style.transform = 'scale(1)';
            }, 10);
        }
    }
    
    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAuthModal();
        }
    });
});

function submitResetPassword(e) {
    e.preventDefault();
    const pass = document.getElementById('reset-password').value;
    const confirmPass = document.getElementById('reset-confirm-password').value;
    const token = document.getElementById('reset-form').dataset.token;
    
    const errorAlert = document.getElementById('reset-feedback-error');
    const errorText = document.getElementById('reset-error-text');
    
    if (!pass || pass.length < 8) {
        errorText.textContent = 'Password must be at least 8 characters.';
        errorAlert.classList.remove('d-none');
        return;
    }
    if (pass !== confirmPass) {
        errorText.textContent = 'Passwords do not match.';
        errorAlert.classList.remove('d-none');
        return;
    }
    if (!token) {
        errorText.textContent = 'Reset link is invalid or has expired.';
        errorAlert.classList.remove('d-none');
        document.getElementById('reset-form').classList.add('d-none');
        document.getElementById('reset-invalid-actions').classList.remove('d-none');
        return;
    }
    
    errorAlert.classList.add('d-none');
    
    const btn = document.getElementById('reset-submit-btn');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...`;
    
    fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: pass, recovery_access_token: token })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById('reset-form').classList.add('d-none');
            document.getElementById('reset-feedback-success').classList.remove('d-none');
            document.getElementById('reset-success-actions').classList.remove('d-none');
            document.getElementById('reset-form').dataset.token = ''; // Clear token
        } else {
            errorText.textContent = data.error?.message || 'Failed to update password. Link may be expired.';
            errorAlert.classList.remove('d-none');
            document.getElementById('reset-form').classList.add('d-none');
            document.getElementById('reset-invalid-actions').classList.remove('d-none');
        }
    })
    .catch(err => {
        errorText.textContent = 'Failed to update password due to a network error.';
        errorAlert.classList.remove('d-none');
        btn.disabled = false;
        btn.innerHTML = `<span>Update Password</span> <i class="bi bi-check-lg fw-bold"></i>`;
    });
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
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Signing In...`;

            fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.value, password: pass.value })
            })
            .then(res => res.json().then(data => ({status: res.status, body: data})))
            .then(result => {
                if (result.status === 200 && result.body.success && result.body.authenticated) {
                    showAlert('Login successful! Redirecting to Journey Planner...', true);
                    setTimeout(() => { navigateToJourneyPlanner(); }, 500);
                } else if (result.status === 401 || result.status === 400 || result.status === 429) {
                    showAlert(result.body.error?.message || 'Invalid email or password.', false);
                    btn.disabled = false;
                    btn.innerHTML = `<span>Log In</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                } else {
                    showAlert('Unable to sign in right now. Please try again.', false);
                    btn.disabled = false;
                    btn.innerHTML = `<span>Log In</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                }
            })
            .catch(err => {
                showAlert('Unable to sign in right now. Please try again.', false);
                btn.disabled = false;
                btn.innerHTML = `<span>Log In</span> <i class="bi bi-arrow-right fw-bold"></i>`;
            });
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
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating Account...`;

            fetch('/api/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: name.value,
                    email: email.value,
                    password: pass.value
                })
            })
            .then(res => res.json().then(data => ({status: res.status, body: data})))
            .then(result => {
                if (result.status === 200 && result.body.success) {
                    if (result.body.authenticated) {
                        showAlert('Account created successfully. You can now log in.', true);
                        document.getElementById('signup-form').reset();
                        switchToTab('login');
                        document.getElementById('login-email').value = email.value;
                        document.getElementById('login-password').focus();
                        btn.disabled = false;
                        btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                    } else if (result.body.requires_email_confirmation) {
                        showAlert('Account created. Please check your email to confirm your account.', true);
                        document.getElementById('signup-form').reset();
                        switchToTab('login');
                        document.getElementById('login-email').value = email.value;
                        document.getElementById('login-password').focus();
                        btn.disabled = false;
                        btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                    } else {
                        showAlert('Unable to sign up right now. Please try again.', false);
                        btn.disabled = false;
                        btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                    }
                } else {
                    showAlert(result.body.error?.message || 'Unable to sign up right now. Please try again.', false);
                    btn.disabled = false;
                    btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
                }
            })
            .catch(err => {
                showAlert('Unable to sign up right now. Please try again.', false);
                btn.disabled = false;
                btn.innerHTML = `<span>Create Account</span> <i class="bi bi-arrow-right fw-bold"></i>`;
            });
        }
    }
}
