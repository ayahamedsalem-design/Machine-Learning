## Technical Questions
1. What is a Dockerfile, and what is its purpose?  
**A Dockerfile:** is a plain-text script containing a series of instructions used to automate the creation of a Docker image.   
**A Dockerfile purpose:** is to provide a reproducible, version-controlled recipe that dictates exactly what environment, dependencies, and configurations an application needs to run, eliminating the "it works on my machine" problem.


2. What is Nginx, and what are its main use cases?  
**Nginx:** is a high-performance open-source web server. Its main use cases include:
* **Web Serving:** Serving static assets (HTML, CSS, images) extremely efficiently.
* **Reverse Proxying:** Routing client requests to backend application servers (like a Python/FastAPI app).
* **Load Balancing:** Distributing incoming traffic across multiple backend servers to prevent overload.
* **SSL Termination:** Managing HTTPS certificates and decrypting traffic before passing it to the internal network.


3. What is a reverse proxy, and how does it work?  
**A reverse proxy:** is an intermediary server that sits in front of one or more backend servers. When a client makes a request, the reverse proxy intercepts it, forwards it to the appropriate backend server, retrieves the response, and returns it to the client.                
**A reverse proxy works:** as a shield, ensuring clients never interact directly with the backend database or application servers, which improves security, allows for caching, and centralizes SSL encryption.

4. What is the difference between Dockerizing an application and running it inside a Virtual Machine (VM)?

| Feature | Docker Container | Virtual Machine (VM) |
|---|---|---|
| **Architecture** | Shares the host OS kernel. | Runs a full guest OS on top of a hypervisor. |
| **Resource Usage** | Lightweight (MBs), dynamically uses RAM/CPU. | Heavy (GBs), requires pre-allocated RAM/CPU. |
| **Startup Time** | Milliseconds to seconds. | Minutes (must boot the entire guest OS). |
| **Isolation** | Process-level isolation. | Complete hardware-level isolation. |


5. What is the difference between a Docker image, a Docker container, and a Docker volume?

| Concept | Definition | State & Lifecycle |
|---|---|---|
| **Docker Image** | A read-only template/blueprint containing the code, runtime, system tools, and libraries. | **Static:** Once built, it does not change. |
| **Docker Container** | A live, running instance of a Docker image executing the application. | **Ephemeral:** If deleted, any internal data is lost. |
| **Docker Volume** | A storage mechanism managed by Docker to persist data outside the container's filesystem. | **Persistent:** Survives container stops and deletions. |