<script setup lang="ts">
import { defineAsyncComponent, onBeforeUnmount, onMounted, ref } from "vue";
import Docs from "./components/Docs.vue";
import FAQPage from "./components/FAQPage.vue";

const logoUrl = "/images/nexaseis_horizontal_notag_white.svg";
const MapView = defineAsyncComponent(() => import("./components/MapView.vue"));
const currentView = ref<"home" | "stations" | "faq" | "docs">("home");

const syncViewFromHistory = () => {
  currentView.value = window.location.pathname === "/faq"
    ? "faq"
    : window.location.pathname === "/docs"
      ? "docs"
      : window.history.state?.nexaseisView === "stations" ? "stations" : "home";
};

const openStationView = () => {
  window.history.pushState({ ...window.history.state, nexaseisView: "stations" }, "", window.location.href);
  currentView.value = "stations";
};

const openFaqView = () => {
  window.history.pushState({ ...window.history.state, nexaseisView: "faq" }, "", "/faq");
  currentView.value = "faq";
};

const openDocsView = () => {
  window.history.pushState({ ...window.history.state, nexaseisView: "docs" }, "", "/docs");
  currentView.value = "docs";
};

const openHomeView = () => {
  window.history.pushState({ ...window.history.state, nexaseisView: "home" }, "", "/");
  currentView.value = "home";
};

onMounted(() => {
  if (!window.history.state?.nexaseisView) {
    window.history.replaceState({ ...window.history.state, nexaseisView: "home" }, "", window.location.href);
  }
  syncViewFromHistory();
  window.addEventListener("popstate", syncViewFromHistory);
});

onBeforeUnmount(() => window.removeEventListener("popstate", syncViewFromHistory));
</script>

<template>
  <div v-if="currentView === 'stations'" class="station-view">
    <MapView />
  </div>

  <v-app v-else>
    <FAQPage v-if="currentView === 'faq'" @back="openHomeView" />
    <Docs v-else-if="currentView === 'docs'" />

    <v-main v-else class="onboarding-page">
      <section class="welcome-panel">
        <img class="welcome-logo" :src="logoUrl" alt="NexaSeis">
        <h1>NexaSeis Collaborative Network</h1>
        <p>Homemade seismic network</p>

        <div class="station-actions">
          <v-btn class="station-action" color="primary" size="large" prepend-icon="mdi-map-marker-multiple" @click="openStationView">
            View stations
          </v-btn>

          <v-btn
            href="https://status.domiko.dev/status/nexaseis"
            target="_blank"
            rel="noopener noreferrer"
            class="station-action"
            color="primary"
            size="large"
            prepend-icon="mdi-server-network"
          >
            Network status
          </v-btn>

          <v-btn class="station-action" color="primary" size="large" prepend-icon="mdi-help-circle-outline" @click="openFaqView">
            FAQ
          </v-btn>

          <v-btn class="station-action" color="primary" size="large" prepend-icon="mdi-book-open-page-variant" @click="openDocsView">
            Docs
          </v-btn>

          <v-btn
            class="station-action"
            color="primary"
            size="large"
            prepend-icon="mdi-github"
            href="https://github.com/Domiko7/NexaSeis"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </v-btn>

          <v-btn
            class="station-action"
            color="primary"
            size="large"
            prepend-icon="mdi-forum"
            href="https://discord.domiko.dev"
            target="_blank"
            rel="noopener noreferrer"
          >
            Discord server
          </v-btn>
        </div>

        <div class="partner-section">
          <div class="partner-logos">
            <a href="https://fdsn.org/networks/detail/Z9_2026/" target="_blank" rel="noopener noreferrer"><img src="/fdsn.png" alt="FDSN"></a>
            <a href="https://globalquake.net/legal/data-attribution" target="_blank" rel="noopener noreferrer"><img src="/gq.png" alt="GlobalQuake"></a>
            <a href="https://ds.iris.edu/ds/nodes/dmc/services/seedlink/" target="_blank" rel="noopener noreferrer"><img src="/earthscope.svg" alt="EarthScope"></a>
          </div>
        </div>

      </section>
    </v-main>
  </v-app>
</template>
