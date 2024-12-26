const canvas = document.getElementById('gameCanvas');
const context = canvas.getContext('2d');
const startButton = document.getElementById('startButton');

let bird = {
    x: 50,
    y: 150,
    radius: 12,
    gravity: 0.6,
    lift: -15,
    velocity: 0,
    color: '#ff0'
};

let pipes = [];
let frameCount = 0;
let score = 0;
let gameRunning = false;

function drawBird() {
    context.beginPath();
    context.arc(bird.x, bird.y, bird.radius, 0, Math.PI * 2);
    context.fillStyle = bird.color;
    context.fill();
    context.closePath();
}

function drawPipes() {
    context.fillStyle = '#228B22';
    pipes.forEach(pipe => {
        context.fillRect(pipe.x, 0, pipe.width, pipe.top);
        context.fillRect(pipe.x, canvas.height - pipe.bottom, pipe.width, pipe.bottom);
    });
}

function updatePipes() {
    if (frameCount % 100 === 0) {
        let gap = 80;
        let top = Math.random() * (canvas.height - gap);
        let bottom = canvas.height - (top + gap);
        pipes.push({ x: canvas.width, width: 20, top: top, bottom: bottom });
    }
    pipes.forEach(pipe => {
        pipe.x -= 2;
    });
    if (pipes.length > 0 && pipes[0].x < -pipes[0].width) {
        pipes.shift();
        score++;
    }
}

function checkCollision() {
    if (bird.y + bird.radius > canvas.height || bird.y - bird.radius < 0) {
        gameRunning = false;
    }
    pipes.forEach(pipe => {
        if (bird.x + bird.radius > pipe.x && bird.x - bird.radius < pipe.x + pipe.width) {
            if (bird.y - bird.radius < pipe.top || bird.y + bird.radius > canvas.height - pipe.bottom) {
                gameRunning = false;
            }
        }
    });
}

function drawScore() {
    context.fillStyle = '#000';
    context.font = '16px Arial';
    context.fillText('Score: ' + score, 10, 20);
}

function update() {
    bird.velocity += bird.gravity;
    bird.y += bird.velocity;
    updatePipes();
    checkCollision();
    if (!gameRunning) {
        alert('Game Over! Your final score is: ' + score);
        startButton.style.display = 'block';
    }
}

function gameLoop() {
    if (gameRunning) {
        context.clearRect(0, 0, canvas.width, canvas.height);
        drawBird();
        drawPipes();
        drawScore();
        update();
        frameCount++;
        requestAnimationFrame(gameLoop);
    }
}

function startGame() {
    bird.y = 150;
    bird.velocity = 0;
    pipes = [];
    score = 0;
    frameCount = 0;
    gameRunning = true;
    startButton.style.display = 'none';
    gameLoop();
}

window.addEventListener('keydown', function(event) {
    if (event.code === 'Space') {
        bird.velocity += bird.lift;
    }
});

startButton.addEventListener('click', startGame);
