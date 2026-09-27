if (!window._cursorWheelInitialized) {
    window._cursorWheelInitialized = true;
    
    window._mouseX = window.innerWidth / 2;
    window._mouseY = window.innerHeight / 2;
    
    document.addEventListener('mousemove', (e) => {
        window._mouseX = e.clientX;
        window._mouseY = e.clientY;
    });

    let time = 0;
    let trailPoints = [];
    let lastMouseX = window.innerWidth / 2;
    let lastMouseY = window.innerHeight / 2;
    let trailActivity = 0;

    function animateWheel() {
        const root = document.getElementById('cursor-wheel-root');
        if (root) {
            const mode = root.getAttribute('data-mode') || 'orbit';
            const items = root.querySelectorAll('.ferris-item');
            const total = items.length;
            
            if (trailPoints.length !== total) {
                trailPoints = Array.from({length: total}, () => ({x: window._mouseX, y: window._mouseY}));
            }

            if (mode === 'trail') {
                root.style.left = '0px';
                root.style.top = '0px';
                
                const dx = window._mouseX - lastMouseX;
                const dy = window._mouseY - lastMouseY;
                const speed = Math.hypot(dx, dy);
                lastMouseX = window._mouseX;
                lastMouseY = window._mouseY;
                
                const targetActivity = Math.min(speed / 15, 1.0); 
                trailActivity += (targetActivity - trailActivity) * 0.15;
                time += 0.02;
                
                const clock4Angle = Math.PI / 4; 
                
                items.forEach((item, index) => {
                    let tX, tY;
                    if (index === 0) {
                        tX = window._mouseX + Math.cos(clock4Angle) * 30;
                        tY = window._mouseY + Math.sin(clock4Angle) * 30;
                    } else {
                        const wave = Math.sin(time * 3 + index) * 6;
                        tX = trailPoints[index - 1].x + Math.cos(clock4Angle) * 28 + wave * 0.2;
                        tY = trailPoints[index - 1].y + Math.sin(clock4Angle) * 28;
                    }
                    
                    if (!trailPoints[index]) {
                        trailPoints[index] = {x: window._mouseX, y: window._mouseY};
                    }
                    
                    trailPoints[index].x += (tX - trailPoints[index].x) * 0.3;
                    trailPoints[index].y += (tY - trailPoints[index].y) * 0.3;
                    
                    // 靜止/圓圈模式計算 (含向下偏移)
                    const angle = index * (2 * Math.PI / total) + time;
                    const radius = 65;
                    const circleOffsetY = 25; 
                    const oX = window._mouseX + radius * Math.cos(angle);
                    const oY = window._mouseY + circleOffsetY + radius * Math.sin(angle);
                
                    const finalX = trailPoints[index].x * trailActivity + oX * (1 - trailActivity);
                    const finalY = trailPoints[index].y * trailActivity + oY * (1 - trailActivity);
                    
                    item.style.transform = `translate(${finalX}px, ${finalY}px)`;
                });
                
            } else {
                // 預設摩天輪 (orbit)
                root.style.left = window._mouseX + 'px';
                root.style.top = window._mouseY + 'px';
                time += 0.02;
                items.forEach((item, index) => {
                    const angle = index * (2 * Math.PI / total);
                    const radius = 75;
                    const theta = time + angle;
                    const x = radius * Math.cos(theta);
                    const y = radius * Math.sin(theta);
                    item.style.transform = `translate(${x}px, ${y}px)`;
                });
            }
        }
        requestAnimationFrame(animateWheel);
    }
    requestAnimationFrame(animateWheel);
}
