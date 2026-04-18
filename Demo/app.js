/* ═══════════════════════════════════════════════
   SSI Academy — Interactive Application Logic
   ═══════════════════════════════════════════════ */

// ── Utilities ──
function generateRandomHex(length) {
    const chars = '0123456789abcdef';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
}

function generateBase58(length) {
    const chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
}

function generateDID() {
    return `did:indy:sovrin:${generateBase58(22)}`;
}

function generateKeyPair() {
    return {
        publicKey: generateBase58(44),
        privateKey: generateBase58(64),
        verkey: generateBase58(44)
    };
}

// ── Particle Background ──
function createParticles() {
    const container = document.getElementById('particles');
    const count = 30;

    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (15 + Math.random() * 25) + 's';
        particle.style.animationDelay = (Math.random() * 20) + 's';
        particle.style.width = (2 + Math.random() * 4) + 'px';
        particle.style.height = particle.style.width;

        const colors = [
            'rgba(139, 92, 246, 0.2)',
            'rgba(59, 130, 246, 0.15)',
            'rgba(236, 72, 153, 0.15)',
            'rgba(6, 182, 212, 0.2)'
        ];
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];

        container.appendChild(particle);
    }
}

// ── Navbar Scroll Effect ──
function initNavbar() {
    const navbar = document.getElementById('navbar');
    const sections = document.querySelectorAll('.section');
    const navLinks = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        // Scrolled class
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }

        // Active section
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 200;
            if (window.scrollY >= sectionTop) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-section') === current) {
                link.classList.add('active');
            }
        });
    });
}

function scrollToSection(id) {
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

// ── Concept Cards ──
function toggleConcept(id) {
    const card = document.getElementById(`concept-${id}`);
    const isExpanded = card.classList.contains('expanded');

    // Close all
    document.querySelectorAll('.concept-card').forEach(c => c.classList.remove('expanded'));

    // Toggle current
    if (!isExpanded) {
        card.classList.add('expanded');
    }
}

// ═══════════════════════════════════════════════
// LIVE DEMO
// ═══════════════════════════════════════════════

let demoState = {
    step: 0,
    issuerDID: null,
    holderDID: null,
    verifierDID: null,
    issuerKeys: null,
    holderKeys: null,
    vc: null,
    vp: null
};

function consolePrint(text, type = '') {
    const body = document.getElementById('console-body');
    const line = document.createElement('div');
    line.className = 'console-line';
    line.innerHTML = `<span class="console-prompt">$</span><span class="console-text ${type}">${text}</span>`;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

function updateStepIndicators(step) {
    for (let i = 1; i <= 4; i++) {
        const indicator = document.getElementById(`step-${i}-indicator`);
        indicator.classList.remove('active', 'completed');

        if (i < step) {
            indicator.classList.add('completed');
        } else if (i === step) {
            indicator.classList.add('active');
        }
    }

    // Connectors
    const connectors = document.querySelectorAll('.step-connector');
    connectors.forEach((c, i) => {
        if (i < step - 1) {
            c.classList.add('done');
        } else {
            c.classList.remove('done');
        }
    });
}

function addBlock(label, data) {
    const blocks = document.getElementById('blockchain-blocks');
    const block = document.createElement('div');
    block.className = 'block';
    block.innerHTML = `<div class="block-label">${label}</div><div class="block-data">${data}</div>`;
    blocks.appendChild(block);

    // scroll to end
    blocks.scrollLeft = blocks.scrollWidth;
}

// ── Step 1: Create DIDs ──
async function demoStep1() {
    const btn = document.getElementById('btn-step-1');
    btn.disabled = true;

    consolePrint('─── ADIM 1: DID Oluşturma ───', 'info');
    await sleep(300);

    // Generate Issuer DID
    consolePrint('🏛️ İTÜ için anahtar çifti üretiliyor...', 'highlight');
    await sleep(500);
    demoState.issuerKeys = generateKeyPair();
    consolePrint(`   Private Key: ${demoState.issuerKeys.privateKey.substring(0, 20)}... (GİZLİ!)`, 'error');
    consolePrint(`   Public Key:  ${demoState.issuerKeys.publicKey.substring(0, 20)}...`, 'success');
    consolePrint(`   Verkey:      ${demoState.issuerKeys.verkey.substring(0, 20)}...`, 'success');
    await sleep(400);

    demoState.issuerDID = generateDID();
    consolePrint(`   DID: ${demoState.issuerDID}`, 'highlight');
    document.getElementById('issuer-did').textContent = demoState.issuerDID;
    document.getElementById('issuer-did').classList.add('has-did');
    document.getElementById('actor-issuer').classList.add('active');

    addBlock('DID: İTÜ', demoState.issuerDID.substring(0, 25) + '...');
    await sleep(600);

    // Generate Holder DID
    consolePrint('👤 Ahmet için anahtar çifti üretiliyor...', 'highlight');
    await sleep(500);
    demoState.holderKeys = generateKeyPair();
    consolePrint(`   Private Key: ${demoState.holderKeys.privateKey.substring(0, 20)}... (GİZLİ!)`, 'error');
    consolePrint(`   Public Key:  ${demoState.holderKeys.publicKey.substring(0, 20)}...`, 'success');
    await sleep(400);

    demoState.holderDID = generateDID();
    consolePrint(`   DID: ${demoState.holderDID}`, 'highlight');
    document.getElementById('holder-did').textContent = demoState.holderDID;
    document.getElementById('holder-did').classList.add('has-did');
    document.getElementById('actor-holder').classList.add('active');
    await sleep(600);

    // Generate Verifier DID
    consolePrint('🏢 Ziraat Bankası için DID oluşturuluyor...', 'highlight');
    await sleep(500);
    demoState.verifierDID = generateDID();
    consolePrint(`   DID: ${demoState.verifierDID}`, 'highlight');
    document.getElementById('verifier-did').textContent = demoState.verifierDID;
    document.getElementById('verifier-did').classList.add('has-did');
    document.getElementById('actor-verifier').classList.add('active');

    addBlock('DID: Banka', demoState.verifierDID.substring(0, 25) + '...');
    await sleep(400);

    // Schema
    consolePrint('📋 "Diploma" Schema\'sı blockchain\'e yazılıyor...', 'warn');
    await sleep(500);
    consolePrint('   Schema: { name: "diploma", version: "1.0", attrs: ["ad", "bolum", "yil", "gpa"] }', 'info');
    addBlock('Schema', 'diploma v1.0');
    await sleep(300);

    // Cred Def
    consolePrint('📝 Credential Definition yayınlanıyor...', 'warn');
    await sleep(400);
    addBlock('Cred Def', 'İTÜ → diploma');

    consolePrint('✅ Tüm DID\'ler ve Schema oluşturuldu!', 'success');

    demoState.step = 1;
    updateStepIndicators(2);
    document.getElementById('btn-step-2').disabled = false;
}

// ── Step 2: Issue VC ──
async function demoStep2() {
    const btn = document.getElementById('btn-step-2');
    btn.disabled = true;

    consolePrint('');
    consolePrint('─── ADIM 2: Diploma VC\'si Verme ───', 'info');
    await sleep(300);

    consolePrint('🏛️ İTÜ, Ahmet\'e diploma VC\'si oluşturuyor...', 'highlight');
    await sleep(600);

    demoState.vc = {
        type: 'UniversityDegreeCredential',
        issuer: demoState.issuerDID,
        subject: demoState.holderDID,
        issuanceDate: new Date().toISOString(),
        claims: {
            ad: 'Ahmet Yılmaz',
            bolum: 'Bilgisayar Mühendisliği',
            mezuniyet_yili: 2024,
            gpa: 3.5
        },
        proof: {
            type: 'Ed25519Signature2018',
            signatureValue: generateBase58(88)
        }
    };

    consolePrint(`   Issuer:  ${demoState.vc.issuer}`, 'info');
    consolePrint(`   Subject: ${demoState.vc.subject}`, 'info');
    consolePrint('   Claims:', 'info');
    consolePrint('     ad: "Ahmet Yılmaz"', '');
    consolePrint('     bölüm: "Bilgisayar Mühendisliği"', '');
    consolePrint('     mezuniyet_yılı: 2024', '');
    consolePrint('     gpa: 3.5', '');
    await sleep(400);

    consolePrint(`   İmza (İTÜ private key ile): ${demoState.vc.proof.signatureValue.substring(0, 30)}...`, 'warn');
    await sleep(500);

    consolePrint('📱 VC, Ahmet\'in cüzdanına gönderiliyor...', 'highlight');
    await sleep(600);

    // Update wallet
    const wallet = document.getElementById('wallet');
    const walletContent = document.getElementById('wallet-content');
    wallet.classList.add('has-vc');
    walletContent.classList.add('has-content');
    walletContent.innerHTML = '🎫 Diploma VC<br>İTÜ - Bilgisayar Müh.<br>Mezuniyet: 2024';

    consolePrint('✅ VC başarıyla cüzdana kaydedildi!', 'success');

    demoState.step = 2;
    updateStepIndicators(3);
    document.getElementById('btn-step-3').disabled = false;
}

// ── Step 3: Create VP ──
async function demoStep3() {
    const btn = document.getElementById('btn-step-3');
    btn.disabled = true;

    consolePrint('');
    consolePrint('─── ADIM 3: VP Oluşturma & Sunma ───', 'info');
    await sleep(300);

    consolePrint('🏢 Ziraat Bankası: "Üniversite diplomanızı gösterin"', 'warn');
    await sleep(600);

    consolePrint('👤 Ahmet VP oluşturuyor (Selective Disclosure)...', 'highlight');
    await sleep(400);

    consolePrint('   ⚠️ Ahmet sadece "bölüm" ve "mezuniyet_yılı" paylaşıyor', 'warn');
    consolePrint('   ❌ "ad" paylaşılMIYOR', 'error');
    consolePrint('   ❌ "gpa" paylaşılMIYOR', 'error');
    await sleep(500);

    demoState.vp = {
        type: 'VerifiablePresentation',
        holder: demoState.holderDID,
        verifiableCredential: [{
            issuer: demoState.issuerDID,
            revealed: {
                bolum: 'Bilgisayar Mühendisliği',
                mezuniyet_yili: 2024
            },
            hidden: ['ad', 'gpa']
        }],
        proof: {
            type: 'Ed25519Signature2018',
            signatureValue: generateBase58(88)
        }
    };

    consolePrint('   VP İçeriği:', 'info');
    consolePrint('     ✅ bölüm: "Bilgisayar Mühendisliği"', 'success');
    consolePrint('     ✅ mezuniyet_yılı: 2024', 'success');
    consolePrint('     🔒 ad: [GİZLİ]', 'error');
    consolePrint('     🔒 gpa: [GİZLİ]', 'error');
    await sleep(500);

    consolePrint(`   VP İmzası (Ahmet private key): ${demoState.vp.proof.signatureValue.substring(0, 30)}...`, 'warn');
    await sleep(400);

    consolePrint('📨 VP Ziraat Bankası\'na gönderiliyor...', 'highlight');
    await sleep(600);

    consolePrint('✅ VP başarıyla gönderildi!', 'success');

    demoState.step = 3;
    updateStepIndicators(4);
    document.getElementById('btn-step-4').disabled = false;
}

// ── Step 4: Verify ──
async function demoStep4() {
    const btn = document.getElementById('btn-step-4');
    btn.disabled = true;

    consolePrint('');
    consolePrint('─── ADIM 4: Doğrulama ───', 'info');
    await sleep(300);

    consolePrint('🏢 Ziraat Bankası VP\'yi doğruluyor...', 'highlight');
    await sleep(600);

    consolePrint('   1️⃣ Blockchain\'den İTÜ\'nün DID\'ini çekiyor...', 'info');
    await sleep(400);
    consolePrint(`      DID: ${demoState.issuerDID}`, '');
    consolePrint(`      Public Key: ${demoState.issuerKeys.publicKey.substring(0, 30)}...`, 'success');
    await sleep(400);

    consolePrint('   2️⃣ Schema kontrol ediliyor...', 'info');
    await sleep(400);
    consolePrint('      Schema: diploma v1.0 ✅', 'success');
    await sleep(300);

    consolePrint('   3️⃣ Credential Definition kontrol ediliyor...', 'info');
    await sleep(400);
    consolePrint('      Cred Def: İTÜ → diploma ✅', 'success');
    await sleep(300);

    consolePrint('   4️⃣ İTÜ\'nün imzası doğrulanıyor...', 'info');
    await sleep(600);
    consolePrint('      İmza geçerli! (Public key ile doğrulandı) ✅', 'success');
    await sleep(300);

    consolePrint('   5️⃣ Ahmet\'in VP imzası doğrulanıyor...', 'info');
    await sleep(400);
    consolePrint('      VP imzası geçerli! ✅', 'success');
    await sleep(300);

    consolePrint('   6️⃣ Revocation kontrol...', 'info');
    await sleep(400);
    consolePrint('      Credential iptal edilmemiş ✅', 'success');
    await sleep(500);

    consolePrint('');
    consolePrint('═══════════════════════════════════════', 'success');
    consolePrint('   🎉 DOĞRULAMA BAŞARILI!', 'success');
    consolePrint('   Ahmet\'in diploması geçerli.', 'success');
    consolePrint('   Bölüm: Bilgisayar Mühendisliği', 'success');
    consolePrint('   Mezuniyet: 2024', 'success');
    consolePrint('   (Ad ve GPA paylaşılmadı — gizli kaldı)', 'warn');
    consolePrint('═══════════════════════════════════════', 'success');

    demoState.step = 4;
    updateStepIndicators(5);

    // Light up verifier
    document.getElementById('actor-verifier').style.borderColor = 'var(--accent-green)';
    document.getElementById('actor-verifier').style.boxShadow = '0 0 30px rgba(16, 185, 129, 0.3)';
}

function resetDemo() {
    demoState = {
        step: 0,
        issuerDID: null,
        holderDID: null,
        verifierDID: null,
        issuerKeys: null,
        holderKeys: null,
        vc: null,
        vp: null
    };

    // Reset buttons
    document.getElementById('btn-step-1').disabled = false;
    document.getElementById('btn-step-2').disabled = true;
    document.getElementById('btn-step-3').disabled = true;
    document.getElementById('btn-step-4').disabled = true;

    // Reset indicators
    updateStepIndicators(1);

    // Reset actors
    document.querySelectorAll('.actor').forEach(a => {
        a.classList.remove('active');
        a.style.borderColor = '';
        a.style.boxShadow = '';
    });
    document.getElementById('issuer-did').textContent = 'DID henüz yok';
    document.getElementById('issuer-did').classList.remove('has-did');
    document.getElementById('holder-did').textContent = 'DID henüz yok';
    document.getElementById('holder-did').classList.remove('has-did');
    document.getElementById('verifier-did').textContent = 'DID henüz yok';
    document.getElementById('verifier-did').classList.remove('has-did');

    // Reset wallet
    const wallet = document.getElementById('wallet');
    const walletContent = document.getElementById('wallet-content');
    wallet.classList.remove('has-vc');
    walletContent.classList.remove('has-content');
    walletContent.textContent = 'Boş';

    // Reset blockchain
    const blocks = document.getElementById('blockchain-blocks');
    blocks.innerHTML = '<div class="block genesis-block"><div class="block-label">Genesis</div></div>';

    // Reset console
    const consoleBody = document.getElementById('console-body');
    consoleBody.innerHTML = '<div class="console-line"><span class="console-prompt">$</span><span class="console-text">Demo sıfırlandı. "Adım 1" butonuna bas.</span></div>';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ═══════════════════════════════════════════════
// QUIZ
// ═══════════════════════════════════════════════

const quizQuestions = [
    {
        q: 'DID (Decentralized Identifier) nedir?',
        options: [
            'Devlet tarafından verilen dijital kimlik numarası',
            'Merkezi olmayan, kendin oluşturduğun benzersiz dijital tanımlayıcı',
            'Bir web sitesinin URL adresi',
            'Blockchain\'deki işlem numarası'
        ],
        correct: 1,
        explanation: 'DID, merkezi bir otoriteye bağlı olmayan, kullanıcının kendisinin oluşturduğu benzersiz bir dijital tanımlayıcıdır.'
    },
    {
        q: 'Private Key (Özel Anahtar) ile ne yapılır?',
        options: [
            'Herkesle paylaşılır',
            'Dijital imza atmak için kullanılır ve gizli tutulur',
            'Blockchain\'e yazılır',
            'DID Document\'te yayınlanır'
        ],
        correct: 1,
        explanation: 'Private Key sadece sahibinde kalır ve dijital imza atmak için kullanılır. Asla paylaşılmaz!'
    },
    {
        q: 'Hyperledger Indy blockchain\'inde hangisi SAKLANMAZ?',
        options: [
            'DID\'ler',
            'Schema tanımları',
            'Kişisel bilgiler (ad, adres, TC no)',
            'Credential Definition\'lar'
        ],
        correct: 2,
        explanation: 'Kişisel bilgiler blockchain\'de saklanmaz! Sadece DID\'ler, Schema\'lar ve Credential Definition\'lar saklanır. Kişisel bilgiler kullanıcının cüzdanında kalır.'
    },
    {
        q: 'Verifiable Presentation (VP) nedir?',
        options: [
            'Blockchain\'deki tüm verilerin görüntülenmesi',
            'Bir VC\'den sadece gerekli bilgilerin seçilerek paylaşılması',
            'Tüm kişisel bilgilerin bir kerede gösterilmesi',
            'Issuer\'ın credential oluşturma süreci'
        ],
        correct: 1,
        explanation: 'VP, bir VC\'den sadece gerekli bilgileri seçerek sunma mekanizmasıdır. Bu sayede "Selective Disclosure" yapılır — örneğin yaşını paylaşıp adını gizleyebilirsin.'
    },
    {
        q: 'SSI sisteminde "Issuer", "Holder" ve "Verifier" rollerinden hangisi doğrudur?',
        options: [
            'Issuer: Credential\'ı doğrular, Holder: verir, Verifier: saklar',
            'Issuer: Credential verir, Holder: cüzdanında saklar, Verifier: doğrular',
            'Hepsi aynı işi yapar',
            'Issuer: Blockchain\'i yönetir, Holder: düğüm çalıştırır'
        ],
        correct: 1,
        explanation: 'Issuer (üniversite gibi) credential verir, Holder (sen) cüzdanında saklar, Verifier (banka gibi) doğrular.'
    }
];

let quizState = {
    currentQuestion: 0,
    score: 0,
    answered: false
};

function renderQuestion() {
    const q = quizQuestions[quizState.currentQuestion];
    document.getElementById('quiz-question').textContent = q.q;
    document.getElementById('q-current').textContent = quizState.currentQuestion + 1;
    document.getElementById('quiz-progress-bar').style.width = ((quizState.currentQuestion / quizQuestions.length) * 100) + '%';

    const optionsContainer = document.getElementById('quiz-options');
    optionsContainer.innerHTML = '';

    q.options.forEach((opt, i) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option';
        btn.textContent = opt;
        btn.onclick = () => selectAnswer(i);
        optionsContainer.appendChild(btn);
    });

    document.getElementById('quiz-feedback').className = 'quiz-feedback';
    document.getElementById('quiz-feedback').style.display = 'none';
    document.getElementById('quiz-next').style.display = 'none';
    quizState.answered = false;
}

function selectAnswer(index) {
    if (quizState.answered) return;
    quizState.answered = true;

    const q = quizQuestions[quizState.currentQuestion];
    const options = document.querySelectorAll('.quiz-option');
    const feedback = document.getElementById('quiz-feedback');

    options.forEach((opt, i) => {
        opt.classList.add('selected');
        if (i === q.correct) {
            opt.classList.add('correct');
        }
        if (i === index && i !== q.correct) {
            opt.classList.add('wrong');
        }
    });

    if (index === q.correct) {
        quizState.score++;
        feedback.className = 'quiz-feedback show correct';
        feedback.textContent = '✅ Doğru! ' + q.explanation;
    } else {
        feedback.className = 'quiz-feedback show wrong';
        feedback.textContent = '❌ Yanlış! ' + q.explanation;
    }
    feedback.style.display = 'block';

    if (quizState.currentQuestion < quizQuestions.length - 1) {
        document.getElementById('quiz-next').style.display = 'block';
        document.getElementById('quiz-next').textContent = 'Sonraki Soru →';
    } else {
        document.getElementById('quiz-next').style.display = 'block';
        document.getElementById('quiz-next').textContent = 'Sonuçları Gör 🎯';
    }
}

function nextQuestion() {
    if (quizState.currentQuestion < quizQuestions.length - 1) {
        quizState.currentQuestion++;
        renderQuestion();
    } else {
        showResults();
    }
}

function showResults() {
    document.getElementById('quiz-question').style.display = 'none';
    document.getElementById('quiz-options').style.display = 'none';
    document.getElementById('quiz-feedback').style.display = 'none';
    document.getElementById('quiz-next').style.display = 'none';
    document.getElementById('quiz-progress-bar').style.width = '100%';

    const result = document.getElementById('quiz-result');
    result.style.display = 'block';

    const ratio = quizState.score / quizQuestions.length;

    if (ratio >= 0.8) {
        document.getElementById('result-icon').textContent = '🏆';
        document.getElementById('result-title').textContent = 'Mükemmel!';
        document.getElementById('result-text').textContent = `${quizState.score}/${quizQuestions.length} doğru! SSI kavramlarını çok iyi anladın.`;
    } else if (ratio >= 0.6) {
        document.getElementById('result-icon').textContent = '👍';
        document.getElementById('result-title').textContent = 'İyi!';
        document.getElementById('result-text').textContent = `${quizState.score}/${quizQuestions.length} doğru! Temel kavramları anladın, biraz daha pratik yapabilirsin.`;
    } else {
        document.getElementById('result-icon').textContent = '📚';
        document.getElementById('result-title').textContent = 'Daha çalışmalısın!';
        document.getElementById('result-text').textContent = `${quizState.score}/${quizQuestions.length} doğru. Kavramlar bölümünü tekrar oku ve dene.`;
    }
}

function restartQuiz() {
    quizState = { currentQuestion: 0, score: 0, answered: false };

    document.getElementById('quiz-question').style.display = 'block';
    document.getElementById('quiz-options').style.display = 'flex';
    document.getElementById('quiz-result').style.display = 'none';

    renderQuestion();
}

// ── Flow Step Hovering ──
function initFlowAnimations() {
    const steps = document.querySelectorAll('.flow-step');
    steps.forEach(step => {
        step.addEventListener('mouseenter', () => {
            step.style.transform = 'translateX(8px)';
        });
        step.addEventListener('mouseleave', () => {
            step.style.transform = 'translateX(0)';
        });
    });
}

// ── Initialize ──
document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    initNavbar();
    initFlowAnimations();
    renderQuestion();

    // Intersection Observer for animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.concept-card, .flow-step, .blockchain-info').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});
