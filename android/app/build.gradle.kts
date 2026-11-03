import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

// Telefona kurulacak (release) APK'nın backend adresi. CI'da workflow girdisinden gelir:
//   ./gradlew assembleRelease -PCINESCOPE_RELEASE_BASE_URL=https://cinescope-api.onrender.com/
// Sonda "/" yoksa eklenir; http:// kabul edilmez (release'te cleartext kapalı).
val releaseBaseUrl: String = providers.gradleProperty("CINESCOPE_RELEASE_BASE_URL")
    .getOrElse("https://cinescope.invalid/")
    .trim()
    .let { if (it.endsWith("/")) it else "$it/" }
    .also { require(it.startsWith("https://")) { "CINESCOPE_RELEASE_BASE_URL https:// ile başlamalı: $it" } }

// Kalıcı imza anahtarı (opsiyonel). Tanımlıysa release APK bununla imzalanır; böylece yeni
// sürümler eski uygulamanın üzerine güncelleme olarak kurulur. Tanımlı değilse debug
// anahtarıyla imzalanır (kişisel kullanım için yeterli). Bkz. KURULUM.md.
val releaseKeystorePath: String? = providers.environmentVariable("CINESCOPE_KEYSTORE_PATH").orNull
val hasReleaseKeystore = releaseKeystorePath != null && file(releaseKeystorePath).exists()

// CI'da her derlemeye artan sürüm kodu verilir (Android güncellemeyi buna göre tanır).
val ciVersionCode: Int = providers.environmentVariable("GITHUB_RUN_NUMBER").orNull?.toIntOrNull() ?: 1

android {
    namespace = "com.cinescope.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.cinescope.app"
        minSdk = 26
        targetSdk = 35
        versionCode = ciVersionCode
        versionName = "1.0.$ciVersionCode"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (hasReleaseKeystore) {
            create("release") {
                storeFile = file(releaseKeystorePath!!)
                storePassword = providers.environmentVariable("CINESCOPE_KEYSTORE_PASSWORD").orNull
                keyAlias = providers.environmentVariable("CINESCOPE_KEY_ALIAS").orNull
                keyPassword = providers.environmentVariable("CINESCOPE_KEY_PASSWORD").orNull
            }
        }
    }

    buildTypes {
        debug {
            // Emülatörden host makineye: localhost yerine 10.0.2.2
            buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:8000/\"")
        }
        release {
            // R8 küçültme kapalı: cihazda doğrulanmamış bir küçültme kuralı çalışma anında
            // çökme riski taşır; APK boyutu kişisel kullanım için sorun değil.
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            buildConfigField("String", "BASE_URL", "\"$releaseBaseUrl\"")
            signingConfig = if (hasReleaseKeystore) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
        // CI: -PwarningsAsErrors=true ile "uyarısız derleme" kapısı zorlanır.
        allWarningsAsErrors.set(
            providers.gradleProperty("warningsAsErrors").map { it.toBoolean() }.orElse(false),
        )
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.androidx.hilt.navigation.compose)

    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)

    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}
