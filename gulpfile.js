var autoprefixer = require('autoprefixer');
var gulp = require('gulp');
var concat = require('gulp-concat');
var cssnano = require('cssnano');
var order = require('gulp-order');
var path = require('path');
var plumber = require('gulp-plumber');
var postcss = require('gulp-postcss');
var sass = require('gulp-sass')(require('sass'));
var uglify = require('gulp-uglify');

const { series } = require('gulp');

function move_css() {
    return gulp.src([
        'node_modules/tabulator-tables/dist/css/tabulator_bootstrap5.min.css',
        'node_modules/tom-select/dist/css/tom-select.bootstrap5.min.css',
        ], {"allowEmpty": true})
        .pipe(gulp.dest('apps/django_bi/src/vendor-css'))
}

function move_js() {
    return gulp.src([
        'node_modules/bootstrap/dist/js/bootstrap.min.js',
        'node_modules/@popperjs/core/dist/umd/popper.min.js',
        'node_modules/tabulator-tables/dist/js/tabulator.min.js',
        'node_modules/sortablejs/Sortable.min.js',
        'node_modules/tom-select/dist/js/tom-select.complete.min.js',
        ], {"allowEmpty": true})
        .pipe(gulp.dest('apps/django_bi/src/vendor-js'))
}

function move_icons() {
        return gulp.src([
            'node_modules/bootstrap-icons/font/bootstrap-icons.min.css',
        ], {"allowEmpty": true})
        .pipe(gulp.dest('apps/django_bi/dist/css'));
}

function move_fonts() {
        return gulp.src([
        'node_modules/bootstrap-icons/font/fonts/*',
        ], {"allowEmpty": true})
        .pipe(gulp.dest('apps/django_bi/dist/fonts'));
}

function img() {
    return gulp.src('apps/django_bi/src/img/**/*', {"allowEmpty": true})
        .pipe(gulp.dest('apps/django_bi/dist/images/'));
}

//function move_alpine_js() {
//    return gulp.src('node_modules/alpinejs/dist/cdn.min.js')
//        .pipe(gulp.dest('apps/django_bi/dist/js'));
//}

function js() {
        return gulp.src(['apps/django_bi/src/js/**/*.js'], {"allowEmpty": true})
        .pipe(plumber())
        .pipe(uglify())
        .pipe(concat('script.min.js'))
        .pipe(gulp.dest('apps/django_bi/dist/js'));
}

function scss() {
    return gulp.src(['apps/django_bi/src/scss/style.scss'])
        .pipe(plumber())
        .pipe(sass())
        .pipe(postcss([autoprefixer(), cssnano()]))
        .pipe(concat('style.min.css'))
        .pipe(gulp.dest('apps/django_bi/dist/css'));
}

function vendor_js() {
        return gulp.src('apps/django_bi/src/vendor-js/*.js', {"allowEmpty": true})
        .pipe(plumber())
        .pipe(order([
                "apps/django_bi/src/vendor-js/popper.min.js",
		        "apps/django_bi/src/vendor-js/bootstrap.min.js",
                "apps/django_bi/src/vendor-js/*.js"
        ], { base: __dirname }))
        .pipe(concat('vendor.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest('apps/django_bi/dist/js'));
}

function vendor_css() {
        return gulp.src('apps/django_bi/src/vendor-css/*.css', {"allowEmpty": true})
        .pipe(plumber())
        .pipe(postcss([autoprefixer(), cssnano()]))
        .pipe(concat('vendor.min.css'))
        .pipe(gulp.dest('apps/django_bi/dist/css'));
}

function production() {
    return gulp.src([
        '../mag360/**/*',
        '!../mag360/venv{,/**}',
        '!../mag360/node_modules{,/**}',
        '!../mag360/debug.log',
        '!../mag360/gulpfile.js',
        '!../mag360/*.json',
        '!../mag360/manage.py',
        '!../mag360/mag360/.env',
        '!../mag360/apps/**/migrations{,/**}',
        '!../mag360/apps/common/src{,/**}',
        '!../mag360/apps/django_bi/src{,/**}',
        '!../mag360/apps/**/__pycache__{,/**}',


//        '!../.git{,/**}',
//        '!../.idea{,/**}',
//        '!../.gitignore',
//        '!../README.md',

	], {"allowEmpty": true})
	.pipe(gulp.dest('C:/Users/n.mantha/Desktop/mag360-production'));
}


exports.move_css = move_css;
exports.move_js = move_js;
exports.move_icons = move_icons;
exports.move_fonts = move_fonts
exports.move = series(move_css, move_js, move_icons, move_fonts);
exports.production = production;

exports.img = img;
exports.js = js;
exports.scss = scss;
exports.vendor_css = vendor_css;
exports.vendor_js = vendor_js;
exports.default = series(img, js, scss, vendor_css, vendor_js);

gulp.task('serve', function () {
        gulp.watch('apps/django_bi/src/img/**/*', gulp.series('img'));
        gulp.watch(['apps/django_bi/src/js/**/*.js'], gulp.series('js'));
        gulp.watch(['apps/django_bi/src/scss/*.scss', 'apps/django_bi/src/scss/*/*.scss'], gulp.series('scss'));
        gulp.watch('apps/django_bi/src/vendor-css/*.css', gulp.series('vendor_css'));
        gulp.watch('apps/django_bi/src/vendor-js/*.js', gulp.series('vendor_js'));
});