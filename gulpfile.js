const gulp = require('gulp');
const less = require('gulp-less');
const sourcemaps = require('gulp-sourcemaps');
const autoprefixer = require('gulp-autoprefixer');
const cleanCSS = require('gulp-clean-css');
const rename = require('gulp-rename');
const uglify = require('gulp-uglify');
const concat = require('gulp-concat');

// Paths
const paths = {
  less: {
    src: 'ckanext/theme_ejemplo/public/base/less/main.less',
    dest: 'ckanext/theme_ejemplo/public/base/css/',
    watch: 'ckanext/theme_ejemplo/public/base/less/**/*.less'
  },
  js: {
    src: 'ckanext/theme_ejemplo/public/base/javascript/**/*.js',
    dest: 'ckanext/theme_ejemplo/public/base/javascript/',
    watch: 'ckanext/theme_ejemplo/public/base/javascript/**/*.js'
  }
};

// Compile Less to CSS
function compileLess() {
  return gulp.src(paths.less.src)
    .pipe(sourcemaps.init())
    .pipe(less())
    .pipe(autoprefixer({
      overrideBrowserslist: ['last 2 versions'],
      cascade: false
    }))
    .pipe(sourcemaps.write('.'))
    .pipe(gulp.dest(paths.less.dest))
    .pipe(cleanCSS({compatibility: 'ie8'}))
    .pipe(rename({ suffix: '.min' }))
    .pipe(gulp.dest(paths.less.dest));
}

// Process JavaScript
function processJS() {
  return gulp.src(paths.js.src)
    .pipe(sourcemaps.init())
    .pipe(concat('main.js'))
    .pipe(sourcemaps.write('.'))
    .pipe(gulp.dest(paths.js.dest))
    .pipe(uglify())
    .pipe(rename({ suffix: '.min' }))
    .pipe(gulp.dest(paths.js.dest));
}

// Watch task
function watchFiles() {
  gulp.watch(paths.less.watch, compileLess);
  gulp.watch(paths.js.watch, processJS);
}

// Define complex tasks
const build = gulp.series(gulp.parallel(compileLess, processJS));
const watch = gulp.series(build, watchFiles);

// Export tasks
exports.less = compileLess;
exports.js = processJS;
exports.build = build;
exports.watch = watch;
exports.default = build;
