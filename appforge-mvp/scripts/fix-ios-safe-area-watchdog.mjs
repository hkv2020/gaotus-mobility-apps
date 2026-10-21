import fs from 'node:fs';
import path from 'node:path';
import { rootDir } from './lib.mjs';

const scenePath = path.join(rootDir, 'ios', 'App', 'App', 'SceneDelegate.swift');
if (!fs.existsSync(scenePath)) throw new Error(`SceneDelegate.swift missing: ${scenePath}`);

let scene = fs.readFileSync(scenePath, 'utf8');
const before = scene;

// v0.8.1 used view.safeAreaInsets from CAPBridgeViewController.viewDidLayoutSubviews().
// CAPBridgeViewController's root view is the WKWebView itself; querying/reframing that
// view while UIKit is resolving scene/status-bar insets can create a layout feedback
// loop during scene creation. Real-device crash evidence showed a 0x8BADF00D
// scene-create watchdog with the main thread in UIWindow/UIStatusBarManager safe-area
// resolution. Remove that patch and keep safe-area ownership outside the bridge view.
const unsafeSafeAreaOverride = /\n\s*override func viewDidLayoutSubviews\(\) \{[\s\S]*?gaotusSafeAreaTopInset[\s\S]*?webView\.scrollView\.contentInsetAdjustmentBehavior = \.never\n\s*\}\n/g;
scene = scene.replace(unsafeSafeAreaOverride, '\n');

const containerMarker = 'final class GaotusSafeAreaContainerViewController: UIViewController {';
if (!scene.includes(containerMarker)) {
  const sceneDelegateMarker = 'class SceneDelegate: UIResponder, UIWindowSceneDelegate {';
  if (!scene.includes(sceneDelegateMarker)) throw new Error('SceneDelegate class marker missing for watchdog-safe safe-area patch');

  const containerSource = `final class GaotusSafeAreaContainerViewController: UIViewController {
    private let content: UIViewController

    init(content: UIViewController) {
        self.content = content
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground

        addChild(content)
        let contentView = content.view!
        contentView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(contentView)
        NSLayoutConstraint.activate([
            contentView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            contentView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            contentView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            contentView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        content.didMove(toParent: self)
    }

    override var childForStatusBarStyle: UIViewController? { content }
    override var childForStatusBarHidden: UIViewController? { content }
}

`;
  scene = scene.replace(sceneDelegateMarker, `${containerSource}${sceneDelegateMarker}`);
}

const directRoot = 'window.rootViewController = GaotusViewController()';
const safeRoot = 'window.rootViewController = GaotusSafeAreaContainerViewController(content: GaotusViewController())';
if (scene.includes(directRoot)) scene = scene.replace(directRoot, safeRoot);
if (!scene.includes(safeRoot)) throw new Error('Unable to bind SceneDelegate root to watchdog-safe safe-area container');

if (scene.includes('gaotusSafeAreaTopInset')) throw new Error('Unsafe v0.8.1 safe-area inset loop is still present');
if (scene.includes('webView.frame = gaotusSafeAreaFrame')) throw new Error('Unsafe v0.8.1 WebView frame mutation is still present');
if (!scene.includes('contentView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor)')) throw new Error('Safe-area top constraint missing');
if (!scene.includes('childForStatusBarStyle')) throw new Error('Status-bar style forwarding missing');

fs.writeFileSync(scenePath, scene);
const report = {
  ok: true,
  mode: 'watchdog-safe-container',
  removedLegacyLayoutOverride: before.includes('gaotusSafeAreaTopInset'),
  rootContainerInstalled: true,
  directSafeAreaReadsInLayoutOverride: false,
  webViewFrameMutationInLayoutOverride: false,
  topConstraint: 'safeAreaLayoutGuide.topAnchor',
  horizontalEdges: 'full-width',
  bottomEdge: 'full-height',
  statusBarForwarding: true,
  verifiedAt: new Date().toISOString()
};
fs.writeFileSync(path.join(rootDir, 'ios-safe-area-watchdog-verification.json'), JSON.stringify(report, null, 2) + '\n');
console.log('[AppForge] iOS watchdog-safe safe-area container applied', JSON.stringify(report));
