# Prerequisite

1. Linux Host (Any OS)
2. Python 3.6+ Installed 
3. Storage is already mapped to the host(FCP, NVMe, etc.)

# Steps to get started

1. Downlaod the folder "dashboard" from Box and copy it in the Linux Host(Initiator) 
2. Install Python 3.6+ and other dependencies for the tool 
    - cd /root/dashboard 
    - python get-pip.py
    - wget https://repo.anaconda.com/archive/Anaconda3-2019.03-Linux-x86_64.sh
    - sh Anaconda3-2019.03-Linux-x86_64.sh
        - Follow the installation via cli
        - Go to next step once installation is over 
    - pip install -r requirements.txt
3. Now connect the storage (if its NVMe, make sure the device is visible via "nvme list")

# Start the Demo 

1. Edit the config.yml file 
    - Make sure, you add the required inputs (Please follow the comments in the "config.yml" file)
2. Run the following:
    - python app.py
    < Let it run >
3. Open any browser and type http://<host_ip>:8050/
    -	Select one of the test from the “Dropdown” and Click on Start 
    -	Once the test gets over, you can do any of the following to start another test:
            - (Recommended)Go to shell command line and press Ctrl+C to stop the application and start the application again (# python app.py) 
                Or 
            - Change any test from the dropdown and click on Start again 


 

