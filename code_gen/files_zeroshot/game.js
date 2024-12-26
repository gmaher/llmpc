const canvas = document.getElementById("gameCanvas");
const context = canvas.getContext("2d");
canvas.width = 640;
canvas.height = 480;

let bird = {
  x: 50,
  y: 150,
  width: 20,
  height: 20,
  gravity: 0.1,
  lift: -5,
  velocity: 0,
};

let pipes = [];
let pipeWidth = 40;
let pipeGap = 250;
let frame = 0;
let score = 0;

function drawBird() {
  context.fillStyle = "#ff0";
  context.fillRect(bird.x, bird.y, bird.width, bird.height);
}

function drawPipes() {
  context.fillStyle = "#0f0";
  pipes.forEach((pipe) => {
    context.fillRect(pipe.x, 0, pipeWidth, pipe.top);
    context.fillRect(
      pipe.x,
      canvas.height - pipe.bottom,
      pipeWidth,
      pipe.bottom
    );
  });
}

function update() {
  bird.velocity += bird.gravity;
  bird.y += bird.velocity;
  if (bird.y + bird.height > canvas.height) {
    bird.y = canvas.height - bird.height;
    bird.velocity = 0;
  }
}

function updatePipes() {
  if (frame % 240 === 0) {
    let top = Math.random() * (canvas.height / 2);
    let bottom = canvas.height - top - pipeGap;
    pipes.push({ x: canvas.width, top: top, bottom: bottom });
  }
  pipes.forEach((pipe) => {
    pipe.x -= 1;
  });
  pipes = pipes.filter((pipe) => pipe.x + pipeWidth > 0);
}

function checkCollisions() {
  pipes.forEach((pipe) => {
    if (
      bird.x < pipe.x + pipeWidth &&
      bird.x + bird.width > pipe.x &&
      (bird.y < pipe.top || bird.y + bird.height > canvas.height - pipe.bottom)
    ) {
      resetGame();
    }
  });
}

function resetGame() {
  bird.y = 150;
  bird.velocity = 0;
  pipes = [];
  score = 0;
}

function updateScore() {
  pipes.forEach((pipe) => {
    if (pipe.x + pipeWidth === bird.x) {
      score++;
    }
  });
  document.getElementById("score").innerText = `Score: ${score}`;
}

function flap() {
  bird.velocity = bird.lift;
}

document.addEventListener("keydown", flap);
document.addEventListener("click", flap);

function gameLoop() {
  context.clearRect(0, 0, canvas.width, canvas.height);
  update();
  updatePipes();
  drawBird();
  drawPipes();
  checkCollisions();
  updateScore();
  frame++;
  requestAnimationFrame(gameLoop);
}

gameLoop();
