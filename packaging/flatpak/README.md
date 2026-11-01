# Flatpak

本目录提供可直接从当前源码树构建的 Flatpak manifest。

## 构建与运行

```bash
# 安装与 manifest 中 runtime-version 对应的 SDK
flatpak install flathub org.gnome.Platform//51 org.gnome.Sdk//51

flatpak-builder --user --install --force-clean \
  build-dir packaging/flatpak/io.github.wubitype.WubiType.yml
flatpak run io.github.wubitype.WubiType
```

如果只需要本地构建、不安装：

```bash
flatpak-builder --force-clean build-dir \
  packaging/flatpak/io.github.wubitype.WubiType.yml
```

## 发布到 Flathub

本地 manifest 使用 `type: dir` 指向源码树，方便开发测试。提交到 Flathub
时，应把 `sources` 改为发布标签对应的 git 源，例如：

```yaml
    sources:
      - type: git
        url: https://github.com/yetist/wubitype.git
        tag: v0.1.0
        commit: <完整的 40 位提交哈希>
```

同时确认 `app-id`、桌面文件中的 `Icon` 名称和图标文件名都使用
`io.github.wubitype.WubiType`。

## 内置文章

`data/text/` 中的练习文章版权归原作者所有。manifest 默认使用
`-Dinstall_articles=false`，不把文章打入 Flatpak。确认授权后可改为
`true`，或把已获授权的文章作为额外的 Flatpak 数据模块安装到
`/app/share/wubitype/text/`。
