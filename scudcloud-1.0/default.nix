with import <nixpkgs> {}; {
  pyEnv = stdenv.mkDerivation {
    name = "py";
    buildInputs = [ stdenv python3 python3Packages.virtualenv python3Packages.pyqt5 sip ];
  };
}