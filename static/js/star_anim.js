document.addEventListener('DOMContentLoaded', function() {
            const canvas = document.querySelector('.star-canvas');
            if (!canvas) return;
            
            // Установка размеров canvas под футер
            function resizeCanvas() {
                const footer = canvas.parentElement;
                canvas.width = footer.clientWidth;
                canvas.height = footer.clientHeight;
            }
            
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            
            const ctx = canvas.getContext("2d");
            const STARS_COUNT = 80; // Оптимальное количество для производительности
            let stars = [];
            let lastTime = 0;
            let frameCount = 0;
            let fps = 60;
            const fpsElement = document.getElementById('fps-counter');
            
            // Цветовая палитра - голубые и фиолетовые оттенки
            const COLOR_PALETTE = [
                '#4cc9f0', '#4895ef', '#4361ee', '#3f37c9', '#3a0ca3',
                '#480ca8', '#560bad', '#7209b7', '#4361ee', '#3a0ca3'
            ];
            
            class Star {
                constructor() {
                    this.size = Math.random() * 1.2 + 0.5;
                    this.x = Math.random() * canvas.width;
                    this.y = Math.random() * canvas.height;
                    this.speedX = (Math.random() - 0.5) * 0.5;
                    this.speedY = Math.random() * 0.3 + 0.1;
                    this.alpha = Math.random() * 0.7 + 0.3;
                    this.color = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)];
                    this.trail = [];
                    this.maxTrailLength = 30;
                    this.flashProgress = 0; // 0 - нет вспышки, 1 - полная вспышка
                    this.flashDirection = 0; // 0 - нет вспышки, 1 - нарастание, -1 - затухание
                    this.flashSize = 0;
                }
                
                update() {
                    // Сохраняем текущую позицию в истории
                    this.trail.push({x: this.x, y: this.y, size: this.size});
                    if (this.trail.length > this.maxTrailLength) {
                        this.trail.shift();
                    }
                    
                    // Обновляем позицию
                    this.x += this.speedX;
                    this.y += this.speedY;
                    
                    // Обработка вспышек
                    if (this.flashDirection === 0 && Math.random() > 0.997) {
                        // Начинаем новую вспышку
                        this.flashDirection = 1;
                        this.flashSize = Math.random() * 2 + 1;
                    }
                    
                    if (this.flashDirection !== 0) {
                        this.flashProgress += this.flashDirection * 0.05;
                        
                        if (this.flashProgress >= 1) {
                            this.flashProgress = 1;
                            this.flashDirection = -1; // начинаем затухание
                        } else if (this.flashProgress <= 0) {
                            this.flashProgress = 0;
                            this.flashDirection = 0; // вспышка завершена
                        }
                    }
                    
                    // Перемещение при выходе за границы
                    if (this.y > canvas.height) {
                        this.y = 0;
                        this.x = Math.random() * canvas.width;
                        this.trail = [];
                    }
                    if (this.y < 0) this.y = canvas.height;
                    if (this.x > canvas.width) this.x = 0;
                    if (this.x < 0) this.x = canvas.width;
                }
                
                draw() {
                    // Рисуем шлейф
                    for (let i = 0; i < this.trail.length; i++) {
                        const point = this.trail[i];
                        const trailAlpha = this.alpha * (i / this.trail.length) * 0.6;
                        const trailSize = this.size * (i / this.trail.length);
                        
                        ctx.beginPath();
                        ctx.fillStyle = this.color;
                        ctx.globalAlpha = trailAlpha;
                        ctx.arc(point.x, point.y, trailSize, 0, Math.PI * 2);
                        ctx.fill();
                    }
                    
                    // Рисуем саму звезду
                    ctx.beginPath();
                    ctx.fillStyle = this.color;
                    ctx.globalAlpha = this.alpha;
                    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Рисуем вспышку, если она активна
                    if (this.flashProgress > 0) {
                        const flashSize = this.size * this.flashSize * this.flashProgress;
                        const flashAlpha = this.flashProgress * 0.7;
                        
                        ctx.beginPath();
                        ctx.fillStyle = '#ffffff';
                        ctx.globalAlpha = flashAlpha;
                        ctx.arc(this.x, this.y, flashSize, 0, Math.PI * 2);
                        ctx.fill();
                    }
                }
            }
            
            // Инициализация звезд
            function initStars() {
                stars = [];
                for (let i = 0; i < STARS_COUNT; i++) {
                    stars.push(new Star());
                }
            }
            
            // Функция анимации
            function animate(timestamp) {
                // Рассчитываем FPS
                frameCount++;
                if (timestamp >= lastTime + 1000) {
                    fps = frameCount;
                    frameCount = 0;
                    lastTime = timestamp;
                    if (fpsElement) fpsElement.textContent = fps;
                }
                
                // Заливаем фон цветом футера
                ctx.fillStyle = '#03121f';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Обновляем и рисуем все звезды
                for (let star of stars) {
                    star.update();
                    star.draw();
                }
                
                requestAnimationFrame(animate);
            }
            
            // Запуск анимации
            initStars();
            requestAnimationFrame(animate);
        });