Name:           wubitype
Version:        0.1.0
Release:        0
Summary:        GTK4 typing tutor for Wubi 98 and 86
License:        MIT
URL:            https://github.com/yetist/wubitype
Source0:        %{url}/archive/refs/tags/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  ninja
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  python3-cairo
BuildRequires:  typelib-1_0-Gtk-4_0
BuildRequires:  typelib-1_0-GdkPixbuf-2_0
BuildRequires:  desktop-file-utils
Requires:       python3-gobject
Requires:       python3-cairo
Requires:       typelib-1_0-Gtk-4_0
Requires:       typelib-1_0-GdkPixbuf-2_0

%description
WubiType is a GTK4 typing tutor for the Wubi 98 and Wubi 86 Chinese
input methods. It provides character, phrase, key-specific and passage
practice, an on-screen keyboard, code lookup, mistake review and
speed/accuracy statistics.

%prep
%autosetup -n %{name}-%{version}

%build
%meson -Dinstall_articles=false
%meson_build

%check
%meson_test

%install
%meson_install
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.wubitype.WubiType.desktop

%files
%license LICENSE
%doc README.md
%{_bindir}/wubitype
%{python3_sitelib}/wubitype
%{_datadir}/wubitype
%{_datadir}/applications/io.github.wubitype.WubiType.desktop
%{_datadir}/metainfo/io.github.wubitype.WubiType.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.wubitype.WubiType.svg
%{_mandir}/man1/wubitype.1*

%changelog
* Sun Nov 01 2026 wubitype contributors <wubitype@example.com> - 0.1.0-0
- Initial package
