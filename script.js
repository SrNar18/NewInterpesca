// ===== BACK TO TOP =====
const backTop = document.getElementById('backTop');
window.addEventListener('scroll', () => {
  backTop.classList.toggle('visible', window.scrollY > 400);
});
backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

// ===== HAMBURGER MENU =====
const hamburger = document.getElementById('hamburger');
const nav = document.getElementById('nav');
hamburger.addEventListener('click', () => nav.classList.toggle('open'));
nav.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => nav.classList.remove('open'));
});

// ===== ANIMATED COUNTERS =====
function animateCounter(el) {
  const target = parseInt(el.dataset.target);
  const duration = 1500;
  const step = target / (duration / 16);
  let current = 0;
  const timer = setInterval(() => {
    current += step;
    if (current >= target) { current = target; clearInterval(timer); }
    el.textContent = Math.floor(current);
  }, 16);
}

const statsSection = document.querySelector('.stats');
const statsObserver = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting) {
    statsSection.classList.add('visible');
    document.querySelectorAll('.stat__number').forEach(animateCounter);
    statsObserver.disconnect();
  }
}, { threshold: 0.35 });
statsObserver.observe(statsSection);

// ===== SCROLL REVEAL =====
const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => revealObserver.observe(el));

// ===== FAQ ACCORDION =====
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.parentElement;
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
    if (!isOpen) item.classList.add('open');
  });
});

// ===== CONTACT FORM =====
const contactForm = document.getElementById('contactForm');
const toast = document.getElementById('toast');

contactForm.addEventListener('submit', async e => {
  e.preventDefault();

  const submitBtn = contactForm.querySelector('[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Enviant...';
  submitBtn.disabled = true;

  const data = {
    nom:      contactForm.querySelector('#f-nom').value,
    empresa:  contactForm.querySelector('#f-empresa').value,
    telefon:  contactForm.querySelector('#f-telefon').value,
    email:    contactForm.querySelector('#f-email').value,
    tipus:    contactForm.querySelector('#f-tipus').value,
    missatge: contactForm.querySelector('#f-missatge').value,
    _subject: 'Nova consulta des de la web Interpesca',
    _template: 'table',
  };

  try {
    const res = await fetch('https://formsubmit.co/ajax/adrianlima8107@gmail.com', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      toast.textContent = 'Gràcies pel teu missatge. Ens posarem en contacte amb tu en el menor temps possible. Si necessites resposta urgent, escriu-nos directament per WhatsApp.';
      toast.classList.remove('toast--error');
    } else {
      throw new Error();
    }
  } catch {
    toast.textContent = 'Hi ha hagut un error en enviar el missatge. Prova-ho de nou o contacta per WhatsApp.';
    toast.classList.add('toast--error');
  }

  toast.classList.add('show');
  contactForm.reset();
  submitBtn.textContent = originalText;
  submitBtn.disabled = false;
  setTimeout(() => toast.classList.remove('show'), 6000);
});
