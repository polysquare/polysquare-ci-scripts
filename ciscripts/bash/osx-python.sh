if [[ "$TRAVIS_OS_NAME" == "osx" ]] ; then
  brew update;
  brew install python python3;
  brew link $PYTHON;
  mkdir -p container
  rm -rf container/venv;
  virtualenv container/venv -p $PYTHON;
  source container/venv/bin/activate;
  pip install --upgrade pip;
  python --version;
fi;
