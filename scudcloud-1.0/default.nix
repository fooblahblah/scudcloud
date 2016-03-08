with import <nixpkgs> {}; {
  pyEnv = stdenv.mkDerivation {
    name = "py";
    buildInputs = [ stdenv python3 python3Packages.virtualenv python3Packages.pyqt5 python3Packages.sip_4_16 qt5.qtmultimedia phonon_qt5 libpulseaudio phonon_qt5_backend_gstreamer gstreamer gst_plugins_base gst_plugins_good gst_plugins_bad glib_networking libsoup cacert ];
    LD_LIBRARY_PATH="${glib_networking}/lib/gio/modules:${libsoup}/lib";
  };
}
