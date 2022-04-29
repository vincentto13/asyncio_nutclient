FROM python:3.10

RUN useradd -ms /bin/bash devel
USER devel
RUN mkdir /home/devel/workspace
WORKDIR /home/devel/workspace
ENV PATH="/home/devel/.local/bin:${PATH}"

RUN pip install build twine


CMD ["/bin/bash"]