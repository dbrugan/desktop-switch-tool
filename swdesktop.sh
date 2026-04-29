sudo sed -i 's/^Session=plasma$/Session=hyprland-uwsm/' /etc/sddm.conf.d/autologin.conf
sudo systemctl restart sddm
