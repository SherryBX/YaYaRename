import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog,
                             QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QProgressBar,
                             QTextEdit, QLabel, QSpinBox, QDialog, QGroupBox, QFormLayout,
                             QDialogButtonBox, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal, QThreadPool, QRunnable, QObject, Qt
import re
import zipfile
import rarfile
import py7zr
from concurrent.futures import ThreadPoolExecutor, as_completed


class WorkerSignals(QObject):
    """工作线程信号"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    file_completed = pyqtSignal(int)  # 新增：单个文件完成信号


class ArchiveWorker(QRunnable):
    """单个文件处理工作线程"""

    def __init__(self, file_path, directory, ext_tag_map):
        super().__init__()
        self.file_path = file_path
        self.directory = directory
        self.ext_tag_map = ext_tag_map
        self.signals = WorkerSignals()

    def get_tag_from_filename(self, filename):
        """从文件名中提取标签"""
        tags = ['3D', 'SU', 'CAD']
        for tag in tags:
            if tag in filename:
                return tag
        return None

    def get_tag_from_content(self, archive_path):
        """从压缩包内容判断标签"""
        file_ext = os.path.splitext(archive_path)[1].lower()

        try:
            if file_ext == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
            elif file_ext == '.rar':
                with rarfile.RarFile(archive_path, 'r') as rar_ref:
                    file_list = rar_ref.namelist()
            elif file_ext == '.7z':
                with py7zr.SevenZipFile(archive_path, 'r') as sz_ref:
                    file_list = sz_ref.getnames()
            else:
                return None

            for filename in file_list:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.ext_tag_map:
                    return self.ext_tag_map[ext]

        except Exception as e:
            self.signals.log.emit(f"处理文件 {archive_path} 时出错: {str(e)}")
            return None

        return None

    def run(self):
        """处理单个文件"""
        try:
            filename = os.path.basename(self.file_path)

            # 1. 检查文件名中是否有标签
            tag = self.get_tag_from_filename(filename)

            # 2. 如果文件名中没有标签，检查压缩包内容
            if not tag:
                tag = self.get_tag_from_content(self.file_path)

            # 3. 如果找到标签，重命名文件
            if tag:
                clean_name = re.sub(r'^(3D|SU|CAD)\s*', '', filename)
                new_name = f"{tag} {clean_name}"
                new_path = os.path.join(self.directory, new_name)

                if self.file_path != new_path:
                    os.rename(self.file_path, new_path)
                    self.signals.log.emit(f"已重命名: {filename} -> {new_name}")

            self.signals.file_completed.emit(1)

        except Exception as e:
            self.signals.log.emit(f"处理文件 {filename} 时出错: {str(e)}")
            self.signals.file_completed.emit(1)


class TagConfigDialog(QDialog):
    """标签配置对话框"""

    def __init__(self, parent=None, current_mappings=None):
        super().__init__(parent)
        self.current_mappings = current_mappings or {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('标签配置')
        layout = QVBoxLayout(self)

        # 文件类型映射配置
        group_box = QGroupBox("文件类型映射配置")
        self.form_layout = QFormLayout()
        group_box.setLayout(self.form_layout)
        layout.addWidget(group_box)

        # 显示现有映射
        self.ext_inputs = {}
        for tag, ext in self.current_mappings.items():
            self.add_mapping_row(tag, ext)

        # 添加新映射的输入区域
        add_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText('新标签')
        self.new_ext_input = QLineEdit()
        self.new_ext_input.setPlaceholderText('新文件类型 (如 .skp)')
        add_layout.addWidget(self.new_tag_input)
        add_layout.addWidget(self.new_ext_input)

        add_btn = QPushButton('添加映射')
        add_btn.clicked.connect(self.add_new_mapping)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # 添加确定和取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_mapping_row(self, tag, ext):
        """添加一行映射配置"""
        row_layout = QHBoxLayout()
        tag_input = QLineEdit(tag)
        ext_input = QLineEdit(ext)
        self.ext_inputs[tag] = ext_input

        row_layout.addWidget(tag_input)
        row_layout.addWidget(ext_input)

        delete_btn = QPushButton('删除')
        delete_btn.clicked.connect(lambda: self.delete_mapping(tag, row_layout))
        row_layout.addWidget(delete_btn)

        self.form_layout.addRow(row_layout)

    def delete_mapping(self, tag, row_layout):
        """删除一行映射配置"""
        # 删除UI元素
        while row_layout.count():
            item = row_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # 从字典中删除
        if tag in self.ext_inputs:
            del self.ext_inputs[tag]

    def add_new_mapping(self):
        """添加新的映射"""
        tag = self.new_tag_input.text().strip()
        ext = self.new_ext_input.text().strip()

        if not tag or not ext:
            return

        if not ext.startswith('.'):
            ext = '.' + ext

        self.add_mapping_row(tag, ext)

        # 清空输入框
        self.new_tag_input.clear()
        self.new_ext_input.clear()

    def get_mappings(self):
        """获取当前配置的映射关系"""
        mappings = {}
        for i in range(self.form_layout.rowCount()):
            row_layout = self.form_layout.itemAt(i, QFormLayout.FieldRole)
            if row_layout:
                tag_input = row_layout.itemAt(0).widget()
                ext_input = row_layout.itemAt(1).widget()
                if tag_input and ext_input:
                    tag = tag_input.text().strip()
                    ext = ext_input.text().strip()
                    if tag and ext:
                        mappings[tag] = ext
        return mappings


class PrefixSuffixConfigDialog(QDialog):
    """前缀后缀配置对话框"""

    def __init__(self, parent=None, is_prefix=True):
        super().__init__(parent)
        self.is_prefix = is_prefix
        self.initUI()

    def initUI(self):
        self.setWindowTitle('前缀配置' if self.is_prefix else '后缀配置')
        layout = QVBoxLayout(self)

        # 常用配置组
        group_box = QGroupBox("常用配置")
        self.form_layout = QFormLayout()
        group_box.setLayout(self.form_layout)
        layout.addWidget(group_box)

        # 添加常用配置
        self.add_common_items()

        # 添加新配置的输入区域
        add_layout = QHBoxLayout()
        self.new_text_input = QLineEdit()
        self.new_text_input.setPlaceholderText('新配置项')
        add_layout.addWidget(self.new_text_input)

        add_btn = QPushButton('添加配置')
        add_btn.clicked.connect(self.add_new_item)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # 添加确定和取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_common_items(self):
        """添加常用配置项"""
        from datetime import datetime

        # 常用配置项
        common_items = []
        if self.is_prefix:
            common_items = [
                ("日期", datetime.now().strftime("%Y%m%d")),
                ("时间", datetime.now().strftime("%H%M%S")),
                ("日期时间", datetime.now().strftime("%Y%m%d_%H%M%S")),
                ("版本", "V1.0"),
                ("草稿", "Draft"),
                ("最终", "Final")
            ]
        else:
            common_items = [
                ("修改日期", datetime.now().strftime("%Y%m%d")),
                ("版本号", "v1.0"),
                ("状态", "完成"),
                ("审核", "待审核"),
                ("备份", "backup")
            ]

        for label, text in common_items:
            self.add_config_row(label, text)

    def add_config_row(self, label, text):
        """添加一行配置"""
        row_layout = QHBoxLayout()

        label_input = QLineEdit(label)
        text_input = QLineEdit(text)
        row_layout.addWidget(label_input)
        row_layout.addWidget(text_input)

        # 使用按钮
        use_btn = QPushButton('使用')
        use_btn.clicked.connect(lambda: self.use_config(text))
        row_layout.addWidget(use_btn)

        # 删除按钮
        delete_btn = QPushButton('删除')
        delete_btn.clicked.connect(lambda: self.delete_config(row_layout))
        row_layout.addWidget(delete_btn)

        self.form_layout.addRow(row_layout)

    def add_new_item(self):
        """添加新配置项"""
        text = self.new_text_input.text().strip()
        if text:
            self.add_config_row(f"自定义{self.form_layout.rowCount() + 1}", text)
            self.new_text_input.clear()

    def delete_config(self, row_layout):
        """删除配置项"""
        while row_layout.count():
            item = row_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def use_config(self, text):
        """使用选中的配置"""
        self.parent().prefix_input.setText(text) if self.is_prefix else self.parent().suffix_input.setText(text)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.total_files = 0
        self.processed_files = 0
        self.ext_tag_map = {
            '.skp': 'SU',
            '.max': '3D',
            '.dwg': 'CAD'
        }
        self.initUI()

    def initUI(self):
        """初始化UI界面"""
        self.setWindowTitle('YaYaRename   Author：Sherry@https://github.com/SherryBX')
        self.setGeometry(300, 300, 800, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 路径选择部分
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText('选择要处理的文件夹路径')
        path_layout.addWidget(self.path_input)

        self.select_btn = QPushButton('选择文件夹')
        self.select_btn.clicked.connect(self.select_directory)
        path_layout.addWidget(self.select_btn)
        layout.addLayout(path_layout)

        # 添加配置按钮
        config_layout = QHBoxLayout()
        self.config_btn = QPushButton('配置文件类型映射')
        self.config_btn.clicked.connect(self.show_config_dialog)
        config_layout.addWidget(self.config_btn)
        config_layout.addStretch()
        layout.addLayout(config_layout)

        # 修改前缀后缀部分
        prefix_suffix_layout = QHBoxLayout()

        # 前缀部分
        prefix_group = QGroupBox("添加前缀")
        prefix_layout = QHBoxLayout()
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText('输入前缀')
        prefix_layout.addWidget(self.prefix_input)

        self.prefix_config_btn = QPushButton('前缀配置')
        self.prefix_config_btn.clicked.connect(self.show_prefix_config)
        prefix_layout.addWidget(self.prefix_config_btn)

        self.add_prefix_btn = QPushButton('添加前缀')
        self.add_prefix_btn.clicked.connect(self.add_prefix)
        prefix_layout.addWidget(self.add_prefix_btn)
        prefix_group.setLayout(prefix_layout)
        prefix_suffix_layout.addWidget(prefix_group)

        # 后缀部分
        suffix_group = QGroupBox("添加后缀")
        suffix_layout = QHBoxLayout()
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText('输入后缀')
        suffix_layout.addWidget(self.suffix_input)

        self.suffix_config_btn = QPushButton('后缀配置')
        self.suffix_config_btn.clicked.connect(self.show_suffix_config)
        suffix_layout.addWidget(self.suffix_config_btn)

        self.add_suffix_btn = QPushButton('添加后缀')
        self.add_suffix_btn.clicked.connect(self.add_suffix)
        suffix_layout.addWidget(self.add_suffix_btn)
        suffix_group.setLayout(suffix_layout)
        prefix_suffix_layout.addWidget(suffix_group)

        layout.addLayout(prefix_suffix_layout)

        # 线程设置部分
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel('处理线程数:'))
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setRange(1, QThread.idealThreadCount())
        self.thread_spinbox.setValue(min(4, QThread.idealThreadCount()))
        thread_layout.addWidget(self.thread_spinbox)
        thread_layout.addStretch()
        layout.addLayout(thread_layout)

        # 开始处理按钮
        self.start_btn = QPushButton('开始处理')
        self.start_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.start_btn)

        # 进度显示
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel('0/0 文件')
        progress_layout.addWidget(self.progress_label)
        layout.addLayout(progress_layout)

        # 日志显示区域
        log_layout = QVBoxLayout()
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("处理日志"))

        # 清空日志按钮
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_header.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addLayout(log_layout)

    def select_directory(self):
        """选择目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            self.path_input.setText(directory)

    def update_progress(self):
        """更新进度显示"""
        self.processed_files += 1
        progress = int(self.processed_files / self.total_files * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f'{self.processed_files}/{self.total_files} 文件')

        if self.processed_files == self.total_files:
            self.processing_finished()

    def start_processing(self):
        """开始处理文件"""
        directory = self.path_input.text()
        if not directory:
            self.log_text.append("请先选择要处理的文件夹")
            return

        # 获取所有压缩文件
        archive_files = [f for f in os.listdir(directory)
                         if f.lower().endswith(('.zip', '.rar', '.7z'))]
        self.total_files = len(archive_files)

        if self.total_files == 0:
            self.log_text.append("未找到压缩文件")
            return

        # 重置进度
        self.processed_files = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText(f'0/{self.total_files} 文件')

        # 禁用开始按钮
        self.start_btn.setEnabled(False)
        self.start_btn.setText("处理中...")

        # 设置线程池最大线程数
        self.thread_pool.setMaxThreadCount(self.thread_spinbox.value())

        # 创建并提交工作线程
        for filename in archive_files:
            file_path = os.path.join(directory, filename)
            worker = ArchiveWorker(file_path, directory, self.ext_tag_map)
            worker.signals.log.connect(self.update_log)
            worker.signals.file_completed.connect(lambda: self.update_progress())
            self.thread_pool.start(worker)

    def update_log(self, message):
        """更新日志"""
        self.log_text.append(message)

    def processing_finished(self):
        """处理完成后的操作"""
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始处理")
        self.log_text.append("所有文件处理完成！")

    def show_config_dialog(self):
        """显示配置对话框"""
        # 转换映射关系为对话框需要的格式
        current_mappings = {v: k for k, v in self.ext_tag_map.items()}
        dialog = TagConfigDialog(self, current_mappings)
        if dialog.exec_() == QDialog.Accepted:
            # 更新文件类型映射
            new_mappings = dialog.get_mappings()
            self.ext_tag_map = {ext: tag for tag, ext in new_mappings.items()}
            self.log_text.append("文件类型映射已更新")

    def add_tag_directly(self):
        """直接添加标签到文件名前"""
        directory = self.path_input.text()
        if not directory:
            self.log_text.append("请先选择要处理的文件夹")
            return

        tag = self.tag_combo.currentText()

        # 获取所有压缩文件
        archive_files = [f for f in os.listdir(directory)
                         if f.lower().endswith(('.zip', '.rar', '.7z'))]

        for filename in archive_files:
            try:
                file_path = os.path.join(directory, filename)
                # 移除已存在的标签
                clean_name = re.sub(r'^(3D|SU|CAD)\s*', '', filename)
                new_name = f"{tag} {clean_name}"
                new_path = os.path.join(directory, new_name)

                if file_path != new_path:
                    os.rename(file_path, new_path)
                    self.log_text.append(f"已添加标签: {filename} -> {new_name}")
            except Exception as e:
                self.log_text.append(f"处理文件 {filename} 时出错: {str(e)}")

        self.log_text.append("标签添加完成！")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def add_prefix(self):
        """添加前缀"""
        directory = self.path_input.text()
        if not directory:
            self.log_text.append("请先选择要处理的文件夹")
            return

        prefix = self.prefix_input.text().strip()
        if not prefix:
            self.log_text.append("请输入要添加的前缀")
            return

        # 获取所有压缩文件
        archive_files = [f for f in os.listdir(directory)
                         if f.lower().endswith(('.zip', '.rar', '.7z'))]

        for filename in archive_files:
            try:
                file_path = os.path.join(directory, filename)
                new_name = f"{prefix} {filename}"
                new_path = os.path.join(directory, new_name)

                if file_path != new_path:
                    os.rename(file_path, new_path)
                    self.log_text.append(f"已添加前缀: {filename} -> {new_name}")
            except Exception as e:
                self.log_text.append(f"处理文件 {filename} 时出错: {str(e)}")

        self.log_text.append("前缀添加完成！")

    def add_suffix(self):
        """添加后缀"""
        directory = self.path_input.text()
        if not directory:
            self.log_text.append("请先选择要处理的文件夹")
            return

        suffix = self.suffix_input.text().strip()
        if not suffix:
            self.log_text.append("请输入要添加的后缀")
            return

        # 获取所有压缩文件
        archive_files = [f for f in os.listdir(directory)
                         if f.lower().endswith(('.zip', '.rar', '.7z'))]

        for filename in archive_files:
            try:
                file_path = os.path.join(directory, filename)
                # 分离文件名和扩展名
                name, ext = os.path.splitext(filename)
                new_name = f"{name} {suffix}{ext}"
                new_path = os.path.join(directory, new_name)

                if file_path != new_path:
                    os.rename(file_path, new_path)
                    self.log_text.append(f"已添加后缀: {filename} -> {new_name}")
            except Exception as e:
                self.log_text.append(f"处理文件 {filename} 时出错: {str(e)}")

        self.log_text.append("后缀添加完成！")

    def show_prefix_config(self):
        """显示前缀配置对话框"""
        dialog = PrefixSuffixConfigDialog(self, is_prefix=True)
        dialog.exec_()

    def show_suffix_config(self):
        """显示后缀配置对话框"""
        dialog = PrefixSuffixConfigDialog(self, is_prefix=False)
        dialog.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())