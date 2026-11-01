# 打包配方

本目录提供 Flatpak 与常见发行版的打包模板。所有配方都从 Meson 构建系统
安装，应用 ID 为 `io.github.wubitype.WubiType`，数据安装到
`/usr/share/wubitype`（Flatpak 中为 `/app/share/wubitype`）。

## 目录

| 目录 | 用途 |
| --- | --- |
| `flatpak/` | Flatpak manifest，可直接从源码树构建 |
| `arch/` | Arch Linux / AUR `PKGBUILD` |
| `fedora/` | Fedora RPM spec |
| `opensuse/` | openSUSE RPM spec |

Debian / Ubuntu 的 `debian/` 目录位于仓库根目录，便于直接运行
`dpkg-buildpackage`。

## 内置文章与再分发

`data/text/` 中的练习文章版权归原作者所有，仓库的 MIT 许可证不覆盖这些
文章。各配方默认使用 `-Dinstall_articles=false`，不安装这些文章：

```bash
meson setup build -Dinstall_articles=false
```

如果已确认所有文章都可以再分发，可改为 `true`。发行版打包时请同时确认
源码包是否包含 `data/text/`；Debian 配方已通过 `Files-Excluded` 将该目录
排除。

## Flatpak

```bash
flatpak install flathub org.gnome.Platform//51 org.gnome.Sdk//51
flatpak-builder --user --install --force-clean \
  build-dir packaging/flatpak/io.github.wubitype.WubiType.yml
flatpak run io.github.wubitype.WubiType
```

详见 `flatpak/README.md`。提交 Flathub 时请把本地 `type: dir` 源替换为
带 tag 和完整 commit 的 `type: git` 源。

## Arch Linux

```bash
cd packaging/arch
makepkg -si
```

`PKGBUILD` 中的 `source` 指向 `v0.1.0` 标签。发布前请把 `sha256sums`
中的 `SKIP` 替换为实际校验值：

```bash
updpkgsums
```

## Debian / Ubuntu

在仓库根目录执行：

```bash
dpkg-buildpackage -us -uc -b
```

需要 `debhelper-compat (>= 13)`、`meson`、`ninja-build`、`python3-gi`、
`python3-gi-cairo`、`gir1.2-gtk-4.0`、`gir1.2-gdkpixbuf-2.0` 等构建依赖。
`debian/watch` 使用 GitHub 标签页，上游地址或仓库位置变化时请同步修改
`debian/control`、`debian/copyright` 和 `debian/watch`。

## Fedora

```bash
rpmbuild -ba packaging/fedora/wubitype.spec
```

## openSUSE

```bash
rpmbuild -ba packaging/opensuse/wubitype.spec
```

## 发布前检查

```bash
desktop-file-validate data/io.github.wubitype.WubiType.desktop
appstreamcli validate --no-net data/io.github.wubitype.WubiType.metainfo.xml
python3 -c 'import yaml; yaml.safe_load(open("packaging/flatpak/io.github.wubitype.WubiType.yml"))'
```

打包配方中的维护者邮箱、上游 URL、版本号和校验值都是模板值，正式发布前
请按实际情况更新。
