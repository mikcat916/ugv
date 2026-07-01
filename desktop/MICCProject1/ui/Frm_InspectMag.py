from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Frm_InspectMag(object):
    def setupUi(self, Frm_InspectMag):
        Frm_InspectMag.setObjectName("Frm_InspectMag")
        Frm_InspectMag.resize(860, 560)
        Frm_InspectMag.setMinimumSize(QtCore.QSize(760, 500))
        Frm_InspectMag.setStyleSheet(
            "QMainWindow {"
            "background: #f3f6fb;"
            "}"
            "QFrame#headerFrame, QFrame#contentFrame, QFrame#footerFrame {"
            "background: #ffffff;"
            "border: 1px solid #dde5f2;"
            "border-radius: 12px;"
            "}"
            "QLabel#titleLabel {"
            "font: 700 24px 'Microsoft YaHei';"
            "color: #1e2b3c;"
            "}"
            "QLabel#subtitleLabel {"
            "font: 12px 'Microsoft YaHei';"
            "color: #627287;"
            "}"
            "QGroupBox {"
            "font: 600 12px 'Microsoft YaHei';"
            "border: 1px solid #dce4f1;"
            "border-radius: 10px;"
            "margin-top: 12px;"
            "padding: 10px;"
            "background: #fcfdff;"
            "}"
            "QGroupBox::title {"
            "subcontrol-origin: margin;"
            "left: 10px;"
            "padding: 0 6px;"
            "color: #30435a;"
            "}"
            "QPushButton {"
            "font: 600 13px 'Microsoft YaHei';"
            "min-height: 44px;"
            "border-radius: 10px;"
            "border: 1px solid #cad5e5;"
            "background: #ffffff;"
            "color: #1f2f44;"
            "padding: 4px 16px;"
            "}"
            "QPushButton:hover {"
            "background: #edf4ff;"
            "border-color: #8db3ff;"
            "}"
            "QPushButton:pressed {"
            "background: #dfeeff;"
            "}"
            "QComboBox {"
            "font: 12px 'Microsoft YaHei';"
            "min-height: 34px;"
            "padding: 4px 10px;"
            "border: 1px solid #cad5e5;"
            "border-radius: 8px;"
            "background: #ffffff;"
            "}"
            "QLabel#statusLabel {"
            "font: 12px 'Microsoft YaHei';"
            "color: #2e3f56;"
            "padding: 2px 4px;"
            "}"
        )

        self.centralWidget = QtWidgets.QWidget(Frm_InspectMag)
        self.centralWidget.setObjectName("centralWidget")
        Frm_InspectMag.setCentralWidget(self.centralWidget)

        self.mainLayout = QtWidgets.QVBoxLayout(self.centralWidget)
        self.mainLayout.setContentsMargins(16, 16, 16, 16)
        self.mainLayout.setSpacing(12)
        self.mainLayout.setObjectName("mainLayout")

        self.headerFrame = QtWidgets.QFrame(self.centralWidget)
        self.headerFrame.setObjectName("headerFrame")
        self.headerLayout = QtWidgets.QVBoxLayout(self.headerFrame)
        self.headerLayout.setContentsMargins(18, 14, 18, 14)
        self.headerLayout.setSpacing(4)
        self.headerLayout.setObjectName("headerLayout")

        self.titleLabel = QtWidgets.QLabel(self.headerFrame)
        self.titleLabel.setObjectName("titleLabel")
        self.headerLayout.addWidget(self.titleLabel)

        self.subtitleLabel = QtWidgets.QLabel(self.headerFrame)
        self.subtitleLabel.setObjectName("subtitleLabel")
        self.headerLayout.addWidget(self.subtitleLabel)

        self.mainLayout.addWidget(self.headerFrame)

        self.contentFrame = QtWidgets.QFrame(self.centralWidget)
        self.contentFrame.setObjectName("contentFrame")
        self.contentLayout = QtWidgets.QVBoxLayout(self.contentFrame)
        self.contentLayout.setContentsMargins(16, 14, 16, 14)
        self.contentLayout.setSpacing(12)
        self.contentLayout.setObjectName("contentLayout")

        self.groupModule = QtWidgets.QGroupBox(self.contentFrame)
        self.groupModule.setObjectName("groupModule")
        self.buttonRow = QtWidgets.QHBoxLayout(self.groupModule)
        self.buttonRow.setContentsMargins(12, 14, 12, 12)
        self.buttonRow.setSpacing(12)
        self.buttonRow.setObjectName("buttonRow")

        self.btn_InspectArea = QtWidgets.QPushButton(self.groupModule)
        self.btn_InspectArea.setObjectName("btn_InspectArea")
        self.buttonRow.addWidget(self.btn_InspectArea)

        self.btn_InspectPoint = QtWidgets.QPushButton(self.groupModule)
        self.btn_InspectPoint.setObjectName("btn_InspectPoint")
        self.buttonRow.addWidget(self.btn_InspectPoint)

        self.btn_InspectRoute = QtWidgets.QPushButton(self.groupModule)
        self.btn_InspectRoute.setObjectName("btn_InspectRoute")
        self.buttonRow.addWidget(self.btn_InspectRoute)

        self.contentLayout.addWidget(self.groupModule)

        self.infoGroup = QtWidgets.QGroupBox(self.contentFrame)
        self.infoGroup.setObjectName("infoGroup")
        self.formLayout = QtWidgets.QFormLayout(self.infoGroup)
        self.formLayout.setContentsMargins(14, 14, 14, 14)
        self.formLayout.setHorizontalSpacing(14)
        self.formLayout.setVerticalSpacing(12)
        self.formLayout.setObjectName("formLayout")

        self.lblArea = QtWidgets.QLabel(self.infoGroup)
        self.lblArea.setObjectName("lblArea")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.lblArea)
        self.txt_InspectArea = QtWidgets.QComboBox(self.infoGroup)
        self.txt_InspectArea.setObjectName("txt_InspectArea")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.txt_InspectArea)

        self.lblRoute = QtWidgets.QLabel(self.infoGroup)
        self.lblRoute.setObjectName("lblRoute")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.lblRoute)
        self.txt_InspectRoute = QtWidgets.QComboBox(self.infoGroup)
        self.txt_InspectRoute.setObjectName("txt_InspectRoute")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.txt_InspectRoute)

        self.contentLayout.addWidget(self.infoGroup)
        self.mainLayout.addWidget(self.contentFrame, 1)

        self.footerFrame = QtWidgets.QFrame(self.centralWidget)
        self.footerFrame.setObjectName("footerFrame")
        self.footerLayout = QtWidgets.QHBoxLayout(self.footerFrame)
        self.footerLayout.setContentsMargins(12, 8, 12, 8)
        self.footerLayout.setObjectName("footerLayout")

        self.statusLabel = QtWidgets.QLabel(self.footerFrame)
        self.statusLabel.setObjectName("statusLabel")
        self.footerLayout.addWidget(self.statusLabel)
        self.mainLayout.addWidget(self.footerFrame)

        self.retranslateUi(Frm_InspectMag)
        QtCore.QMetaObject.connectSlotsByName(Frm_InspectMag)

    def retranslateUi(self, Frm_InspectMag):
        _translate = QtCore.QCoreApplication.translate
        Frm_InspectMag.setWindowTitle(_translate("Frm_InspectMag", "巡检管理"))
        self.titleLabel.setText(_translate("Frm_InspectMag", "巡检管理中心"))
        self.subtitleLabel.setText(_translate("Frm_InspectMag", "统一管理巡检区域、点位与路线，支持快速进入对应模块"))
        self.groupModule.setTitle(_translate("Frm_InspectMag", "模块入口"))
        self.btn_InspectArea.setText(_translate("Frm_InspectMag", "巡检区域"))
        self.btn_InspectPoint.setText(_translate("Frm_InspectMag", "巡检点位"))
        self.btn_InspectRoute.setText(_translate("Frm_InspectMag", "巡检路线"))
        self.infoGroup.setTitle(_translate("Frm_InspectMag", "当前数据"))
        self.lblArea.setText(_translate("Frm_InspectMag", "当前区域"))
        self.lblRoute.setText(_translate("Frm_InspectMag", "当前路线"))
        self.statusLabel.setText(_translate("Frm_InspectMag", "请选择要进入的模块"))
