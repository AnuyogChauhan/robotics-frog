tag = robot-network
tag1 = $(tag)-ens
ports = -p 5001:50051
enstag = 127.0.0.1:5000/ens/workloadrobot-network

proto:
	python -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. ./messages.proto

build:
	cp Dockerfile Dockerfile.ens
	cp Dockerfile.traditional Dockerfile
	docker build -t $(tag) ./
	mv Dockerfile.ens Dockerfile
	
runinteractive: stop
	docker run -it --name=$(tag) $(ports) $(tag)
	
run: stop
	docker run -d --name=$(tag) $(ports) $(tag)
	
stop:
	docker stop $(tag) || echo "$(tag) not running"
	docker rm $(tag) || echo "$(tag) container not found"

buildens:
	docker rmi -f $(enstag) || echo "no such image"
	docker build -t $(enstag) ./
	docker push $(enstag)
	
test:
	python tests.py
