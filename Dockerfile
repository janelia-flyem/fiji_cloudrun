# Pull base JDK-8 image.
FROM openjdk:8

######Install Fiji ######

# Create directory for fiji install 
RUN mkdir /opt/fiji

# Define working directory.
WORKDIR /opt/fiji

# Add fiji to the PATH
ENV PATH $PATH:/opt/fiji/Fiji.app


RUN wget -q https://downloads.imagej.net/fiji/latest/fiji-nojre.zip \
 && unzip fiji-nojre.zip \
 && rm fiji-nojre.zip

##### install conda #######

COPY install-miniconda.sh /opt/docker/bin/install-miniconda.sh                                                        
RUN /opt/docker/bin/install-miniconda.sh                                                                              

# Add a timestamp for the build. Also, bust the cache.                                                                
RUN date > container-build-date.txt 

ENV FLYEM_ENV /opt/conda/envs/flyem 
ENV PATH /opt/conda/bin:${PATH}                                   

# Install packages                                                                                                    
RUN conda create -n flyem python=3.7 flask flask-cors gunicorn google-cloud-storage pillow 

# Ensure that flyem/bin is on the PATH                                                                                
ENV PATH ${FLYEM_ENV}/bin:${PATH}                                   

#### update fiji ######

# Update URLs use https
RUN ImageJ-linux64 --update edit-update-site ImageJ https://update.imagej.net/
RUN ImageJ-linux64 --update edit-update-site Fiji https://update.fiji.sc/
RUN ImageJ-linux64 --update edit-update-site Java-8 https://sites.imagej.net/Java-8/

##### make user just for fiji

# Create a user and fiji run directory
RUN useradd -u 1000 -ms /bin/bash fiji
RUN mkdir /opt/fiji_run && chown fiji:fiji /opt/fiji_run

##### launch server under root user which will sandbox user requests ######

COPY fiji.py /opt/fiji/ 
COPY process_request.py /opt/fiji/ 
WORKDIR /opt/fiji
CMD exec ${FLYEM_ENV}/bin/gunicorn --bind :$PORT --workers 1 --threads 1 fiji:app --timeout 900
