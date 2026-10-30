docker ps --all
docker stop resume-tweaker
docker rm resume-tweaker

# 1. Build the image
docker --context default build -t resume-tweaker:latest .

# 2. Create and start the container
docker --context default run -d --name resume-tweaker \
  --restart unless-stopped \
  --read-only --tmpfs /tmp \
  -p 127.0.0.1:8080:80 \
  resume-tweaker:latest