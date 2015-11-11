#! /bin/bash
sudo mkdir -p /mnt/pd0
sudo /usr/share/google/safe_format_and_mount -m "mkfs.ext4 -F" /dev/disk/by-id/google-skia-autoroll-data /mnt/pd0
sudo chmod 777 /mnt/pd0

pushd /home/default
# Install depot_tools if needed.
if [[ ! -d depot_tools ]]; then
  sudo -u default git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
fi

# Add depot_tools to PATH if needed.
if [ -z "$(which gclient)" ]; then
  sudo -u default echo '# Add depot_tools to PATH"' >> .bashrc
  sudo -u default echo 'export PATH="/home/default/depot_tools:$PATH"' >> .bashrc
fi

popd