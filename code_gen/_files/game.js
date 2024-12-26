const canvas = document.getElementById("gameCanvas");
const context = canvas.getContext("2d");

let birdImage = new Image();
birdImage.src = "bird.png";

let pipeImage = new Image();
pipeImage.src = "pipe.png";

let bird = {
  x: 50,
  y: 150,
  width: 50,
  height: 50,
  gravity: 0.05,
  lift: -4,
  velocity: 0,
};

let pipes = [];
let pipeWidth = 40;
let pipeGap = 280;
let pipeInterval = 360; // Frames between pipe generations
let frames = 0;
let gameOver = false;
let score = 0;

function resetGame() {
  bird.y = 150;
  bird.velocity = 0;
  pipes = [];
  frames = 0;
  score = 0;
  gameOver = false;
  gameLoop();
}

document.addEventListener("keydown", function (event) {
  if (event.code === "Space") {
    bird.velocity += bird.lift;
  } else if (gameOver && event.code === "Enter") {
    resetGame();
  }
});

canvas.addEventListener("click", function () {
  if (gameOver) {
    resetGame();
  }
});

function generatePipe() {
  let pipeHeight =
    Math.floor(Math.random() * (canvas.height - pipeGap - 20)) + 10;
  pipes.push({
    x: canvas.width,
    topHeight: pipeHeight,
    bottomY: pipeHeight + pipeGap,
    width: pipeWidth,
    passed: false,
  });
}

function update() {
  bird.velocity += bird.gravity;
  bird.y += bird.velocity;

  if (bird.y + bird.height > canvas.height || bird.y < 0) {
    gameOver = true;
  }

  pipes.forEach((pipe) => {
    pipe.x -= 1;
    if (pipe.x + pipe.width < 0) {
      pipes.shift();
    }

    if (
      bird.x < pipe.x + pipe.width &&
      bird.x + bird.width > pipe.x &&
      (bird.y < pipe.topHeight || bird.y + bird.height > pipe.bottomY)
    ) {
      gameOver = true;
    }

    if (!pipe.passed && pipe.x + pipe.width < bird.x) {
      score++;
      pipe.passed = true;
    }
  });

  if (frames % pipeInterval === 0) {
    generatePipe();
  }

  frames++;
}

function draw() {
  context.clearRect(0, 0, canvas.width, canvas.height);

  context.drawImage(birdImage, bird.x, bird.y, bird.width, bird.height);

  pipes.forEach((pipe) => {
    context.drawImage(pipeImage, pipe.x, 0, pipe.width, pipe.topHeight);
    context.drawImage(
      pipeImage,
      pipe.x,
      pipe.bottomY,
      pipe.width,
      canvas.height - pipe.bottomY
    );
  });

  context.font = "24px serif";
  context.fillStyle = "black";
  context.fillText("Score: " + score, 10, 30);
}

function gameLoop() {
  if (!gameOver) {
    update();
    draw();
    requestAnimationFrame(gameLoop);
  } else {
    context.font = "48px serif";
    context.fillStyle = "black";
    context.fillText("Game Over", canvas.width / 4, canvas.height / 2);
    context.font = "24px serif";
    context.fillText(
      "Press Enter or Click to Restart",
      canvas.width / 6,
      canvas.height / 2 + 40
    );
  }
}

gameLoop();
