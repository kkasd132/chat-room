let previewSettings = {}; // 預覽暫存設定
// 初始化設定
function initSettings() {
    const saved = JSON.parse(localStorage.getItem('chatSettings') || '{}');
    previewSettings = { ...saved }; // 初始值 = 已儲存的設定
    updateUI(previewSettings); // 預覽
    // 從 localStorage 載入設定
    const settings = JSON.parse(localStorage.getItem('chatSettings')) || {};
    
    // 背景類型
    if(settings.bgType === 'image') {
        document.getElementById('bg-image').checked = true;
        document.querySelector('.image-preview').style.backgroundImage = `url(${settings.bgImage})`;
    } else {
        document.getElementById('bg-color').checked = true;
        document.querySelector('.color-picker').value = settings.bgColor || '#ffffff';
    }

    // 字體顏色
    if(settings.fontColor) {
        document.querySelector('.font-color-picker').value = settings.fontColor;
    }

    // 模糊度
    if(settings.blurValue) {
        document.getElementById('blur-range').value = settings.blurValue;
        document.getElementById('blur-value').textContent = `${settings.blurValue * 10}%`;
    }

    // 事件監聽
    document.querySelector('.image-upload').addEventListener('change', handleImageUpload);
    document.getElementById('blur-range').addEventListener('input', updateBlurValue);
    document.querySelectorAll('.theme-preset').forEach(preset => {
        preset.addEventListener('click', applyPresetTheme);
    });
    document.querySelector('.color-picker').addEventListener('input', (e) => {
        previewSettings.bgColor = e.target.value;
        previewSettings.bgType = 'color';
        previewSettings.themeType = 'custom';
        updateUI(previewSettings);
    });
    document.querySelector('.font-color-picker').addEventListener('input', (e) => {
        previewSettings.fontColor = e.target.value;
        updateUI(previewSettings);
    });

}
function updateUI(settings) {
    // 背景
    if (settings.bgType === 'image') {
        document.getElementById('bg-image').checked = true;
        document.querySelector('.image-preview').style.backgroundImage = `url(${settings.bgImage})`;
        document.querySelector('.chat-background').style.background = `url(${settings.bgImage}) center/cover`;
    } else {
        document.getElementById('bg-color').checked = true;
        document.querySelector('.color-picker').value = settings.bgColor || '#ffffff';
        document.querySelector('.chat-background').style.background = settings.bgColor || '#ffffff';
    }

    // 模糊
    const blurPx = `${settings.blurValue || 0}px`;
    document.getElementById('blur-range').value = settings.blurValue || 0;
    document.getElementById('blur-value').textContent = `${(settings.blurValue || 0) * 10}%`;
    document.querySelector('.chat-background').style.filter = `blur(${blurPx})`;

    // 字體
    document.querySelector('.font-color-picker').value = settings.fontColor || '#2c3e50';
    document.documentElement.style.setProperty('--font-color', settings.fontColor || '#2c3e50');
}

function updateBlurValue(e) {
    const value = e.target.value;
    previewSettings.blurValue = parseInt(value);
    updateUI(previewSettings);  // 即時預覽
}

function applyPresetTheme(e) {
    const bgStyle = e.target.style.background;
    const isGradient = bgStyle.includes('gradient');

    if (isGradient) {
        previewSettings.bgColor = bgStyle;
        previewSettings.bgType = 'color';
        previewSettings.themeType = 'default';
    } else {
        previewSettings.bgImage = bgStyle;
        previewSettings.bgType = 'image';
        previewSettings.themeType = 'default';
    }

    updateUI(previewSettings);
}

function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    fetch('/upload_bg_image', {
        method: 'POST',
        body: formData
    }).then(res => res.json()).then(data => {
        if (data.success) {
            previewSettings.bgImage = data.url;
            previewSettings.bgType = 'image';
            updateUI(previewSettings);
        } else {
            alert(data.message || '圖片上傳失敗');
        }
    }).catch(() => alert('上傳錯誤'));
}

function applySettings() {
    localStorage.setItem('chatSettings', JSON.stringify(previewSettings));

    const { bgType, bgColor, fontColor, blurValue, bgImage } = previewSettings;

    fetch('/save_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            bg_color: bgType === 'image' ? '' : bgColor,
            font_color: fontColor || '#000000',
            blur: blurValue || 0,
            custom_bg: bgType === 'image' ? bgImage : ''
        })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            window.location.href = '/';
        } else {
            alert('儲存設定失敗');
        }
    }).catch(() => alert('網路錯誤'));
}
