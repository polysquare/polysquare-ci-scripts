if [[ "$TRAVIS_OS_NAME" == "osx" ]] ; then
  brew update;
  brew install $PYTHON;
  brew link $PYTHON;
  mkdir -p container
  rm -rf container/venv;
  virtualenv container/venv -p $PYTHON;
  pip install --upgrade pip;
  source container/venv/bin/activate;
fi;
