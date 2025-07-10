        // 初始化設定
        function initSettings() {
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
        }

        function handleImageUpload(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const preview = document.querySelector('.image-preview');
                    preview.style.backgroundImage = `url(${event.target.result})`;
                    localStorage.setItem('chatSettings', JSON.stringify({
                        ...JSON.parse(localStorage.getItem('chatSettings') || '{}'),
                        bgImage: event.target.result,
                        bgType: 'image'
                    }));
                }
                reader.readAsDataURL(file);
            }
        }

        function updateBlurValue(e) {
            const value = e.target.value;
            document.getElementById('blur-value').textContent = `${value * 10}%`;
            localStorage.setItem('chatSettings', JSON.stringify({
                ...JSON.parse(localStorage.getItem('chatSettings') || '{}'),
                blurValue: value
            }));
        }

        function applyPresetTheme(e) {
            const bgImage = e.target.style.backgroundImage;
            document.querySelector('.image-preview').style.backgroundImage = bgImage;
            localStorage.setItem('chatSettings', JSON.stringify({
                ...JSON.parse(localStorage.getItem('chatSettings') || '{}'),
                bgImage: bgImage.replace(/url\(["']?(.*?)["']?\)/, '$1'),
                bgType: 'image'
            }));
        }

function applySettings() {
    const settings = JSON.parse(localStorage.getItem('chatSettings') || '{}');
    
    // 應用背景
    if(settings.bgType === 'image') {
        document.body.style.background = `url(${settings.bgImage}) center/cover`;
    } else {
        document.body.style.background = settings.bgColor;
    }
    
    // 應用模糊度
    document.body.style.backdropFilter = `blur(${settings.blurValue || 0}px)`;
    
    // 應用字體顏色
    document.documentElement.style.setProperty('--font-color', settings.fontColor || '#2c3e50');
    
    // 返回聊天室
    window.history.back();
}
