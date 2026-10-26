project(
  'wubitype',
  version: '0.1.0',
  meson_version: '>=0.61.0',
)

python = import('python').find_installation('python3')
gnome = import('gnome')

datadir = get_option('datadir')
app_id = 'io.github.wubitype.WubiType'
data_install_dir = join_paths(datadir, 'wubitype')

# Python 包
install_subdir(
  'src/wubitype',
  install_dir: python.get_install_dir(),
  exclude_directories: ['__pycache__', 'ui/__pycache__'],
)

# 启动脚本
install_data(
  'data/wubitype',
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

# 码表和键位图
install_data(
  [
    'data/wubi98.main.txt',
    'data/wubi98.large.txt',
    'data/wubi98-table.png',
    'data/wubi86.main.txt',
    'data/wubi86.large.txt',
    'data/wubi86-table.png',
  ],
  install_dir: data_install_dir,
)

# 桌面集成
install_data(
  'data/io.github.wubitype.WubiType.desktop',
  install_dir: join_paths(datadir, 'applications'),
)

install_data(
  'data/io.github.wubitype.WubiType.metainfo.xml',
  install_dir: join_paths(datadir, 'metainfo'),
)

install_data(
  'data/icons/hicolor/scalable/apps/io.github.wubitype.WubiType.svg',
  install_dir: join_paths(datadir, 'icons', 'hicolor', 'scalable', 'apps'),
)

install_man('data/wubitype.1')

# 单元测试
test(
  'unit',
  python,
  args: [
    '-m',
    'unittest',
    'discover',
    '-s',
    join_paths(meson.current_source_dir(), 'tests'),
    '-v',
  ],
  env: [
    'PYTHONPATH=' + join_paths(meson.current_source_dir(), 'src'),
  ],
  timeout: 120,
)

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
